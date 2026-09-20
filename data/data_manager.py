from __future__ import annotations

import json

import pandas as pd

from data.dnse_client import DNSEDataClient
from data.vnstock_client import VnstockFundamentalClient
from data.realtime_client import VnstockRealtimeClient


class DataManager:
    """
    Lớp quản lý và chuẩn hóa dữ liệu cho stock bot.

    Nguồn dữ liệu:
    - DNSE: giá thị trường OHLCV lịch sử
    - VNStock VCI: dữ liệu tài chính cơ bản
    - VNStock Quote: dữ liệu giao dịch gần real-time
    """

    def __init__(self):
        self.dnse = DNSEDataClient()
        self.vnstock = VnstockFundamentalClient()
        self.realtime = VnstockRealtimeClient()

    # ============================================================
    # DNSE - MARKET DATA
    # ============================================================

    @staticmethod
    def _parse_dnse_ohlcv(response_text: str) -> pd.DataFrame:
        """
        Chuyển JSON response từ DNSE thành DataFrame.

        DNSE trả về:
        {
            "t": [...],
            "o": [...],
            "h": [...],
            "l": [...],
            "c": [...],
            "v": [...],
            "nextTime": 0
        }
        """

        if not response_text:
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "datetime",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            )

        data = json.loads(response_text)

        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        length = min(
            len(timestamps),
            len(opens),
            len(highs),
            len(lows),
            len(closes),
            len(volumes),
        )

        records = []

        for i in range(length):
            timestamp = timestamps[i]

            records.append(
                {
                    "timestamp": timestamp,
                    "datetime": (
                        pd.to_datetime(
                            timestamp,
                            unit="s",
                            utc=True,
                        ).tz_convert("Asia/Ho_Chi_Minh")
                    ),
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i],
                    "volume": volumes[i],
                }
            )

        df = pd.DataFrame(records)

        if not df.empty:
            df = df.sort_values(
                "timestamp",
                ascending=True,
            ).reset_index(drop=True)

        return df

    def get_market_data(
        self,
        symbol: str,
        start_timestamp: int,
        end_timestamp: int,
        resolution: str = "1D",
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu OHLCV lịch sử từ DNSE.
        """

        response_text = self.dnse.get_historical_ohlcv(
            symbol=symbol.upper(),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution=resolution,
        )

        df = self._parse_dnse_ohlcv(response_text)

        if not df.empty:
            df.insert(
                0,
                "symbol",
                symbol.upper(),
            )

        return df

    # ============================================================
    # VNSTOCK - FUNDAMENTAL DATA
    # ============================================================

    def get_fundamental_data(
        self,
        symbol: str,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu tài chính năm từ VNStock.
        """

        return self.vnstock.get_annual_fundamentals(
            symbol.upper()
        )

    # ============================================================
    # COMBINED DATA
    # ============================================================

    def get_combined_data(
        self,
        symbol: str,
        start_timestamp: int,
        end_timestamp: int,
        resolution: str = "1D",
    ) -> pd.DataFrame:
        """
        Kết hợp dữ liệu thị trường và dữ liệu tài chính.
        """

        market_df = self.get_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution=resolution,
        )

        fundamental_df = self.get_fundamental_data(
            symbol=symbol,
        )

        if market_df.empty:
            return market_df

        if fundamental_df.empty:
            return market_df

        market_df = market_df.copy()
        fundamental_df = fundamental_df.copy()

        market_df["year"] = (
            market_df["datetime"]
            .dt.year
            .astype(str)
        )

        fundamental_df["report_period"] = (
            fundamental_df["report_period"].astype(str)
        )

        combined_df = market_df.merge(
            fundamental_df,
            left_on=["symbol", "year"],
            right_on=["symbol", "report_period"],
            how="left",
            suffixes=("", "_fundamental"),
        )

        combined_df = combined_df.drop(
            columns=[
                "year",
                "report_period",
            ],
            errors="ignore",
        )

        return combined_df

    # ============================================================
    # LATEST FUNDAMENTAL
    # ============================================================

    def get_latest_fundamental(
        self,
        symbol: str,
    ) -> pd.Series:
        """
        Lấy bộ dữ liệu tài chính mới nhất.
        """

        df = self.get_fundamental_data(symbol)

        if df.empty:
            return pd.Series(dtype="object")

        return df.iloc[0]

    # ============================================================
    # LATEST MARKET DATA
    # ============================================================

    def get_latest_market_data(
        self,
        symbol: str,
        start_timestamp: int,
        end_timestamp: int,
        resolution: str = "1D",
    ) -> pd.Series:
        """
        Lấy phiên giao dịch mới nhất trong khoảng thời gian.
        """

        df = self.get_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution=resolution,
        )

        if df.empty:
            return pd.Series(dtype="object")

        return df.iloc[-1]

    # ============================================================
    # REAL-TIME MARKET DATA
    # ============================================================

    def get_realtime_trade(
        self,
        symbol: str,
    ) -> dict:
        """
        Lấy giao dịch khớp lệnh gần nhất của cổ phiếu.

        Returns
        -------
        dict
            Gồm:
            - symbol
            - time
            - price
            - volume
            - match_type
            - id
        """

        return self.realtime.get_latest_trade(
            symbol=symbol,
        )

    # ============================================================
    # STOCK SNAPSHOT
    # ============================================================

    def get_stock_snapshot(
        self,
        symbol: str,
        start_timestamp: int,
        end_timestamp: int,
        resolution: str = "1D",
    ) -> dict:
        """
        Trả về snapshot kết hợp giữa:
        - giá thị trường mới nhất
        - dữ liệu tài chính mới nhất
        """

        latest_market = self.get_latest_market_data(
            symbol=symbol,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution=resolution,
        )

        latest_fundamental = self.get_latest_fundamental(
            symbol=symbol
        )

        realtime_trade = self.get_realtime_trade(
            symbol=symbol
        )

        snapshot = {
            "symbol": symbol.upper(),
            "market": (
                latest_market.to_dict()
                if not latest_market.empty
                else {}
            ),
            "realtime": realtime_trade,
            "fundamental": (
                latest_fundamental.to_dict()
                if not latest_fundamental.empty
                else {}
            ),
        }

        return snapshot


class MarketDataManager:
    """
    Quản lý dữ liệu thị trường mở rộng.

    Hiện tại hỗ trợ:
    - Lấy dữ liệu lịch sử VN-Index từ DNSE.
    """

    def __init__(self):
        self.dnse = DNSEDataClient()

    def get_historical_index(
        self,
        index_symbol: str = "VNINDEX",
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu VN-Index trong số ngày gần nhất.

        Parameters
        ----------
        index_symbol : str
            Mã chỉ số, mặc định VNINDEX.

        days : int
            Số ngày lịch sử cần lấy.

        Returns
        -------
        pd.DataFrame
            DataFrame gồm:
            timestamp
            datetime
            open
            high
            low
            close
            volume
        """

        if days <= 0:
            raise ValueError("days phải lớn hơn 0")

        now_utc = pd.Timestamp.now(tz="UTC")

        end_timestamp = int(
            now_utc.timestamp()
        )

        start_timestamp = int(
            (
                now_utc
                - pd.Timedelta(days=days)
            ).timestamp()
        )

        response_text = self.dnse.get_historical_index(
            index_symbol=index_symbol.upper(),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            resolution="1D",
        )

        return DataManager._parse_dnse_ohlcv(
            response_text
        )