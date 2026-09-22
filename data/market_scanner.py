from __future__ import annotations

import time
from typing import Optional

import pandas as pd

from vnstock import Listing

from data.ssi_client import SSIDataClient


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
        "HOSE": "HOSE",
        "HNX": "HNX",
        "UPCOM": "UPCoM",
        "UPCOM": "UPCoM",
    }

    def __init__(
        self,
        request_delay: float = 0.15,
    ):
        self.listing = Listing()
        self.ssi = SSIDataClient()
        self.request_delay = request_delay

    # ========================================================
    # Lấy danh sách cổ phiếu
    # ========================================================

    def get_stock_universe(self) -> pd.DataFrame:
        """
        Lấy danh sách toàn bộ mã cổ phiếu từ VNStock Listing.

        VNStock trả về các cột:
            symbol
            organ_name
            en_organ_name
            exchange
            type
            ...

        Chỉ giữ:
            symbol
            market
        """

        # ----------------------------------------------------
        # VNStock all_symbols() hiện chỉ trả symbol + organ_name
        # nên dùng symbols_by_exchange() để lấy exchange.
        # ----------------------------------------------------

        df = self.listing.symbols_by_exchange(
            "HOSE"
        )

        if df is None or df.empty:
            raise ValueError(
                "VNStock không trả về danh sách cổ phiếu."
            )

        if "symbol" not in df.columns:
            raise ValueError(
                "VNStock listing thiếu cột symbol."
            )

        if "exchange" not in df.columns:
            raise ValueError(
                "VNStock listing thiếu cột exchange."
            )

        df = df.copy()

        # ----------------------------------------------------
        # Chuẩn hóa symbol
        # ----------------------------------------------------

        df["symbol"] = (
            df["symbol"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        # ----------------------------------------------------
        # Chuẩn hóa exchange
        # ----------------------------------------------------

        df["exchange"] = (
            df["exchange"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

        # ----------------------------------------------------
        # Chỉ giữ cổ phiếu hợp lệ
        # ----------------------------------------------------

        df = df[
            df["symbol"].notna()
            & (df["symbol"] != "")
        ]

        # ----------------------------------------------------
        # Chuyển exchange -> market
        # ----------------------------------------------------

        df["market"] = (
            df["exchange"]
            .map(self.MARKET_MAP)
        )

        # ----------------------------------------------------
        # Loại những mã không xác định được sàn
        # ----------------------------------------------------

        df = df[
            df["market"].notna()
        ]

        # ----------------------------------------------------
        # Chỉ giữ symbol + market
        # ----------------------------------------------------

        df = (
            df[
                [
                    "symbol",
                    "market",
                ]
            ]
            .drop_duplicates(
                subset=["symbol"]
            )
            .sort_values(
                "symbol"
            )
            .reset_index(drop=True)
        )

        if df.empty:
            raise ValueError(
                "Không tìm thấy mã cổ phiếu hợp lệ."
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
        Lấy dữ liệu OHLCV gần nhất của một mã
        từ SSI iBoard.
        """

        end_timestamp = int(
            time.time()
        )

        start_timestamp = (
            end_timestamp
            - days * 24 * 60 * 60
        )

        start_date = (
            pd.to_datetime(
                start_timestamp,
                unit="s",
                utc=True,
            )
            .tz_convert(
                "Asia/Ho_Chi_Minh"
            )
            .strftime("%d/%m/%Y")
        )

        end_date = (
            pd.to_datetime(
                end_timestamp,
                unit="s",
                utc=True,
            )
            .tz_convert(
                "Asia/Ho_Chi_Minh"
            )
            .strftime("%d/%m/%Y")
        )

        df = self.ssi.get_historical_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            return pd.DataFrame()

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