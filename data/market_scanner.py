from __future__ import annotations

import time
from typing import Optional

import pandas as pd

from .dnse_client import DNSEDataClient


class MarketScanner:
    """
    Quét diễn biến cổ phiếu trên toàn bộ thị trường Việt Nam.

    Hỗ trợ:
    - HOSE
    - HNX
    - UPCoM

    Chức năng:
    - Lấy giá đóng cửa gần nhất
    - Tính % thay đổi so với phiên trước
    - Phân loại tăng / giảm / đứng giá
    - Lấy Top mã tăng
    - Lấy Top mã giảm
    """

    MARKET_MAP = {
        "STO": "HOSE",
        "STX": "HNX",
        "UPX": "UPCoM",
    }

    def __init__(
        self,
        request_delay: float = 0.15,
    ):
        self.dnse = DNSEDataClient()
        self.request_delay = request_delay

    # ========================================================
    # Lấy danh sách cổ phiếu
    # ========================================================

    def get_stock_universe(self) -> pd.DataFrame:
        """
        Lấy toàn bộ danh sách cổ phiếu từ DNSE.

        DNSE giới hạn tối đa 1000 instruments mỗi request,
        nên sử dụng pagination bằng offset.

        Chỉ giữ securityGroupId = ST.
        """

        import json

        all_items = []

        limit = 1000
        offset = 0

        while True:

            result = self.dnse.client._request(
                "GET",
                "/market/instruments",
                query={
                    "securityGroupId": "ST",
                    "limit": limit,
                    "offset": offset,
                },
            )

            status_code, response_text = result

            if status_code != 200:
                raise RuntimeError(
                    f"DNSE instruments API error: "
                    f"{status_code} - {response_text}"
                )

            data = response_text

            if isinstance(data, str):
                data = json.loads(data)

            if isinstance(data, dict):
                items = (
                    data.get("data")
                    or data.get("items")
                    or data.get("instruments")
                    or []
                )
            elif isinstance(data, list):
                items = data
            else:
                items = []

            if not items:
                break

            all_items.extend(items)

            # Nếu số lượng trả về nhỏ hơn limit,
            # nghĩa là đã tới trang cuối.
            if len(items) < limit:
                break

            offset += limit

        if not all_items:
            raise ValueError(
                "DNSE không trả về danh sách cổ phiếu."
            )

        rows = []

        for item in all_items:

            if not isinstance(item, dict):
                continue

            symbol = item.get("symbol")

            if not symbol:
                continue

            security_group = item.get(
                "securityGroupId"
            )

            if security_group != "ST":
                continue

            market_id = item.get("marketId")

            rows.append(
                {
                    "symbol": str(symbol).upper(),
                    "market_id": market_id,
                    "market": self.MARKET_MAP.get(
                        market_id,
                        market_id,
                    ),
                }
            )

        df = pd.DataFrame(rows)

        if df.empty:
            raise ValueError(
                "Không tìm thấy cổ phiếu thuộc nhóm ST."
            )

        df = (
            df.drop_duplicates(
                subset=["symbol"]
            )
            .sort_values(
                ["market", "symbol"]
            )
            .reset_index(drop=True)
        )

        return df

    # ========================================================
    # Lấy dữ liệu giá của một mã
    # ========================================================

    def _get_stock_price_data(
        self,
        symbol: str,
        days: int = 5,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu OHLCV gần nhất của một mã.
        """

        end_timestamp = int(
            time.time()
        )

        start_timestamp = (
            end_timestamp
            - days * 24 * 60 * 60
        )

        response_text = (
            self.dnse.get_historical_ohlcv(
                symbol=symbol,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                resolution="1D",
            )
        )

        return self._parse_ohlcv(
            response_text
        )

    # ========================================================
    # Parse OHLCV
    # ========================================================

    @staticmethod
    def _parse_ohlcv(
        response_text,
    ) -> pd.DataFrame:

        import json

        if isinstance(response_text, str):
            response_text = json.loads(
                response_text
            )

        if isinstance(response_text, dict):
            data = (
                response_text.get("data")
                or response_text.get("items")
                or response_text
            )
        else:
            data = response_text

        if isinstance(data, dict):
            timestamps = (
                data.get("t")
                or data.get("timestamp")
                or []
            )

            opens = (
                data.get("o")
                or data.get("open")
                or []
            )

            highs = (
                data.get("h")
                or data.get("high")
                or []
            )

            lows = (
                data.get("l")
                or data.get("low")
                or []
            )

            closes = (
                data.get("c")
                or data.get("close")
                or []
            )

            volumes = (
                data.get("v")
                or data.get("volume")
                or []
            )

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                    "volume": volumes,
                }
            )

        elif isinstance(data, list):

            df = pd.DataFrame(data)

            rename_map = {
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
            }

            df = df.rename(
                columns=rename_map
            )

        else:
            return pd.DataFrame()

        required_columns = [
            "timestamp",
            "close",
            "volume",
        ]

        for column in required_columns:
            if column not in df.columns:
                return pd.DataFrame()

        df["timestamp"] = pd.to_numeric(
            df["timestamp"],
            errors="coerce",
        )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "timestamp",
                "close",
            ]
        )

        if df.empty:
            return df

        df["datetime"] = pd.to_datetime(
            df["timestamp"],
            unit="s",
            utc=True,
        ).dt.tz_convert(
            "Asia/Ho_Chi_Minh"
        )

        df = df.sort_values(
            "datetime"
        ).reset_index(
            drop=True
        )

        return df

    # ========================================================
    # Phân tích một mã
    # ========================================================

    def analyze_stock(
        self,
        symbol: str,
        market: Optional[str] = None,
    ) -> Optional[dict]:

        try:
            df = self._get_stock_price_data(
                symbol=symbol,
                days=5,
            )

            if len(df) < 2:
                return None

            latest = df.iloc[-1]
            previous = df.iloc[-2]

            close = float(
                latest["close"]
            )

            previous_close = float(
                previous["close"]
            )

            volume = float(
                latest["volume"]
            )

            if previous_close == 0:
                return None

            change_pct = (
                (
                    close
                    - previous_close
                )
                / previous_close
                * 100
            )

            return {
                "symbol": symbol,
                "market": market,
                "close": close,
                "previous_close": previous_close,
                "change_pct": change_pct,
                "volume": volume,
            }

        except Exception:
            return None

    # ========================================================
    # Quét toàn thị trường
    # ========================================================

    def scan_market(
        self,
        universe: Optional[pd.DataFrame] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:

        if universe is None:
            universe = (
                self.get_stock_universe()
            )

        if limit is not None:
            universe = universe.head(
                limit
            )

        results = []

        for _, row in universe.iterrows():

            symbol = row["symbol"]
            market = row["market"]

            result = self.analyze_stock(
                symbol=symbol,
                market=market,
            )

            if result is not None:
                results.append(result)

            if self.request_delay > 0:
                time.sleep(
                    self.request_delay
                )

        if not results:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "market",
                    "close",
                    "previous_close",
                    "change_pct",
                    "volume",
                ]
            )

        return pd.DataFrame(
            results
        )

    # ========================================================
    # Thống kê độ rộng
    # ========================================================

    @staticmethod
    def market_breadth(
        df: pd.DataFrame,
    ) -> dict:

        if df.empty:
            return {
                "total": 0,
                "advancing": 0,
                "declining": 0,
                "unchanged": 0,
            }

        advancing = int(
            (df["change_pct"] > 0).sum()
        )

        declining = int(
            (df["change_pct"] < 0).sum()
        )

        unchanged = int(
            (df["change_pct"] == 0).sum()
        )

        return {
            "total": len(df),
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
        }

    # ========================================================
    # Top tăng / giảm
    # ========================================================

    @staticmethod
    def top_gainers(
        df: pd.DataFrame,
        n: int = 10,
    ) -> pd.DataFrame:

        if df.empty:
            return df.copy()

        return (
            df[df["change_pct"] > 0]
            .sort_values(
                "change_pct",
                ascending=False,
            )
            .head(n)
            .reset_index(drop=True)
        )

    @staticmethod
    def top_losers(
        df: pd.DataFrame,
        n: int = 10,
    ) -> pd.DataFrame:

        if df.empty:
            return df.copy()

        return (
            df[df["change_pct"] < 0]
            .sort_values(
                "change_pct",
                ascending=True,
            )
            .head(n)
            .reset_index(drop=True)
        )

    # ========================================================
    # Thống kê theo sàn
    # ========================================================

    @staticmethod
    def breadth_by_market(
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        if df.empty:
            return pd.DataFrame()

        rows = []

        for market, group in df.groupby(
            "market"
        ):

            breadth = (
                MarketScanner.market_breadth(
                    group
                )
            )

            rows.append(
                {
                    "market": market,
                    **breadth,
                }
            )

        return pd.DataFrame(
            rows
        )