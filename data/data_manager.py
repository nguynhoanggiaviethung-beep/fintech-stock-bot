from __future__ import annotations

import json

import pandas as pd

from data.dnse_client import DNSEDataClient
from data.ssi_client import SSIDataClient
from data.vnstock_client import VnstockFundamentalClient
from data.realtime_client import VnstockRealtimeClient
from data.market_cache import MarketCache
from vnstock import Market


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
        self.ssi = SSIDataClient()
        self.vnstock = VnstockFundamentalClient()
        self.realtime = VnstockRealtimeClient()
        self.market_manager = MarketDataManager()
        

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
        Lấy dữ liệu OHLCV lịch sử cổ phiếu từ SSI iBoard.

        SSI:
            Historical stock OHLCV

        VNStock:
            Fundamental data

        VNStock Quote:
            Realtime trade
        """

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "symbol không được để trống"
            )

        if resolution != "1D":
            raise ValueError(
                "SSI historical hiện chỉ được "
                "sử dụng với resolution=1D."
            )

        start_date = (
            pd.to_datetime(
                start_timestamp,
                unit="s",
                utc=True,
            )
            .tz_convert("Asia/Ho_Chi_Minh")
            .strftime("%d/%m/%Y")
        )

        end_date = (
            pd.to_datetime(
                end_timestamp,
                unit="s",
                utc=True,
            )
            .tz_convert("Asia/Ho_Chi_Minh")
            .strftime("%d/%m/%Y")
        )

        print(
            f"[DATA MANAGER] "
            f"Historical {symbol}: "
            f"dùng SSI "
            f"{start_date} -> {end_date}",
            flush=True,
        )

        df = self.ssi.get_historical_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            raise ValueError(
                f"SSI không trả dữ liệu "
                f"historical cho {symbol}."
            )

        print(
            f"[DATA MANAGER] "
            f"Historical {symbol}: "
            f"SSI OK ({len(df)} rows)",
            flush=True,
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

    Hỗ trợ:
    - Dữ liệu lịch sử cổ phiếu từ DNSE
    - Dữ liệu lịch sử VN-Index từ DNSE
    """

    def __init__(self):
        self.dnse = DNSEDataClient()
        self.vnstock_client = VnstockFundamentalClient()
        self.realtime_client = VnstockRealtimeClient()
        self.vnstock_market = Market()
        self.cache = MarketCache()


    # ============================================================
# GENERIC MARKET DATA
# ============================================================

    def get_market_data(
        self,
        symbol: str = "VNINDEX",
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        resolution: str = "1D",
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu thị trường.

        - VNINDEX: lấy dữ liệu Index từ VNStock Market.
        - Mã cổ phiếu: lấy dữ liệu historical từ SSI.
        """

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "symbol không được để trống"
            )

        # ========================================================
        # VNINDEX + khoảng thời gian cụ thể
        # ========================================================

        if (
            start_timestamp is not None
            and end_timestamp is not None
        ):

            if symbol == "VNINDEX":

                if resolution != "1D":
                    raise ValueError(
                        "VNINDEX hiện chỉ hỗ trợ resolution=1D."
                    )

                start_date = pd.to_datetime(
                    start_timestamp,
                    unit="s",
                ).strftime("%Y-%m-%d")

                end_date = pd.to_datetime(
                    end_timestamp,
                    unit="s",
                ).strftime("%Y-%m-%d")

                print(
                    "[MARKET MANAGER] "
                    f"VNINDEX: VNStock "
                    f"{start_date} -> {end_date}",
                    flush=True,
                )

                market = self.vnstock_market.index(
                    symbol
                )

                df = market.ohlcv(
                    start=start_date,
                    end=end_date,
                    interval="1D",
                )

                if df is None or df.empty:
                    return pd.DataFrame(
                        columns=[
                            "symbol",
                            "timestamp",
                            "datetime",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ]
                    )

                df = df.copy()

                if "time" in df.columns:
                    df = df.rename(
                        columns={
                            "time": "datetime"
                        }
                    )

                required_columns = [
                    "datetime",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]

                missing_columns = [
                    column
                    for column in required_columns
                    if column not in df.columns
                ]

                if missing_columns:
                    raise ValueError(
                        "VNStock VNINDEX thiếu cột: "
                        + ", ".join(
                            missing_columns
                        )
                    )

                df["datetime"] = pd.to_datetime(
                    df["datetime"]
                )

                numeric_columns = [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]

                for column in numeric_columns:
                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce",
                    )

                df = df.dropna(
                    subset=[
                        "datetime",
                        *numeric_columns,
                    ]
                )

                df["timestamp"] = (
                    df["datetime"]
                    .astype("int64")
                    // 10**9
                )

                df.insert(
                    0,
                    "symbol",
                    symbol,
                )

                df = df[
                    [
                        "symbol",
                        "timestamp",
                        "datetime",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ]
                ].sort_values(
                    "datetime"
                ).reset_index(
                    drop=True
                )

                self.cache.set(df)

                print(
                    "[MARKET MANAGER] "
                    f"VNINDEX: nhận {len(df)} phiên",
                    flush=True,
                )

                return df

            # ====================================================
            # Cổ phiếu + khoảng thời gian cụ thể
            # ====================================================

            return self._get_stock_history(
                symbol=symbol,
                days=max(
                    1,
                    int(
                        (
                            end_timestamp
                            - start_timestamp
                        ) / 86400
                    ),
                ),
                resolution=resolution,
            )

        # ========================================================
        # Không truyền timestamp
        # ========================================================

        if symbol == "VNINDEX":
            return self.get_historical_index(
                index_symbol=symbol,
                days=days,
            )

        return self._get_stock_history(
            symbol=symbol,
            days=days,
            resolution=resolution,
        )

    # ============================================================
    # STOCK HISTORY
    # ============================================================

    # ============================================================
    # STOCK HISTORY
    # ============================================================

    def _get_stock_history(
        self,
        symbol: str,
        days: int = 30,
        resolution: str = "1D",
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử cổ phiếu từ SSI iBoard.

        SSI:
            Historical stock OHLCV

        Dữ liệu trả về được chuẩn hóa về format:
            symbol
            timestamp
            datetime
            open
            high
            low
            close
            volume
        """

        if days <= 0:
            raise ValueError(
                "days phải lớn hơn 0"
            )

        if resolution != "1D":
            raise ValueError(
                "SSI historical hiện chỉ hỗ trợ "
                "resolution=1D."
            )

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "symbol không được để trống"
            )

        # ========================================================
        # TÍNH KHOẢNG NGÀY
        # ========================================================

        end_date = pd.Timestamp.now(
            tz="Asia/Ho_Chi_Minh"
        )

        start_date = (
            end_date
            - pd.Timedelta(days=days)
        )

        start_date_str = start_date.strftime(
            "%d/%m/%Y"
        )

        end_date_str = end_date.strftime(
            "%d/%m/%Y"
        )

        print(
            f"[DATA MANAGER] "
            f"Historical {symbol}: "
            f"dùng SSI "
            f"{start_date_str} -> {end_date_str}",
            flush=True,
        )

        # ========================================================
        # GỌI SSI
        # ========================================================

        df = self.ssi.get_historical_ohlcv(
            symbol=symbol,
            start_date=start_date_str,
            end_date=end_date_str,
        )

        if df is None or df.empty:
            raise ValueError(
                f"SSI không trả dữ liệu historical "
                f"cho {symbol}."
            )

        # ========================================================
        # KIỂM TRA CỘT
        # ========================================================

        required_columns = [
            "symbol",
            "timestamp",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "SSI thiếu các cột: "
                + ", ".join(missing_columns)
            )

        # ========================================================
        # CHUẨN HÓA
        # ========================================================

        df = df[
            required_columns
        ].copy()

        df["symbol"] = (
            df["symbol"]
            .fillna(symbol)
            .astype(str)
            .str.upper()
        )

        df["datetime"] = pd.to_datetime(
            df["datetime"]
        )

        numeric_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        df = df.dropna(
            subset=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

        df = (
            df
            .sort_values("datetime")
            .drop_duplicates(
                subset=[
                    "symbol",
                    "datetime",
                ],
                keep="last",
            )
            .reset_index(drop=True)
        )

        if df.empty:
            raise ValueError(
                f"SSI không còn dữ liệu hợp lệ "
                f"sau khi chuẩn hóa {symbol}."
            )

        # ========================================================
        # CACHE
        # ========================================================

        self.cache.set(df)

        print(
            f"[DATA MANAGER] "
            f"Historical {symbol}: "
            f"SSI OK ({len(df)} rows)",
            flush=True,
        )

        return df
    # ============================================================
    # VN-INDEX
    # ============================================================

    def get_historical_index(
        self,
        index_symbol: str = "VNINDEX",
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu VN-Index trong số ngày gần nhất từ DNSE.
        Bổ sung: Bắt lỗi Timeout và fallback lấy từ Cache nếu API DNSE lỗi.
        """
        if days <= 0:
            raise ValueError("days phải lớn hơn 0")

        index_symbol = index_symbol.upper().strip()

        now_utc = pd.Timestamp.now(tz="UTC")

        end_timestamp = int(now_utc.timestamp())

        start_timestamp = int(
            (now_utc - pd.Timedelta(days=days)).timestamp()
        )

        try:
            # Gọi API DNSE
            response_text = self.dnse.get_historical_index(
                index_symbol=index_symbol,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                resolution="1D",
            )

            df = DataManager._parse_dnse_ohlcv(response_text)

            if not df.empty:
                df.insert(0, "symbol", index_symbol)
                # Lưu vào cache để dự phòng cho các lần gọi sau bị timeout
                if hasattr(self, "cache") and self.cache:
                    self.cache.set(df)
                return df

        except Exception as e:
            print(f"[MARKET WARNING] Lỗi/Timeout khi gọi DNSE Index ({e}). Đang dùng Cache...")

        # FALLBACK: Nếu gọi DNSE thất bại/timeout, lấy dữ liệu cũ từ Cache
        if hasattr(self, "cache") and self.cache:
            cached_df = self.cache.get()
            if cached_df is not None and not cached_df.empty:
                return cached_df

        return pd.DataFrame(
            columns=[
                "symbol", "timestamp", "datetime", "open", "high", "low", "close", "volume"
            ]
        )