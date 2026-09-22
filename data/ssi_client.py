from __future__ import annotations

import pandas as pd
import requests


class SSIDataClient:
    """
    Client lấy dữ liệu lịch sử giá cổ phiếu
    từ SSI iBoard API.
    """

    BASE_URL = (
        "https://iboard-api.ssi.com.vn"
        "/statistics/company/ssmi"
    )

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @staticmethod
    def _empty_dataframe() -> pd.DataFrame:
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

    def get_historical_ohlcv(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        page_size: int = 100,
    ) -> pd.DataFrame:

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "symbol không được để trống"
            )

        if page_size <= 0:
            raise ValueError(
                "page_size phải lớn hơn 0"
            )

        url = f"{self.BASE_URL}/stock-info"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }

        all_records = []
        page = 1

        while True:

            params = {
                "symbol": symbol,
                "page": page,
                "pageSize": page_size,
                "fromDate": start_date,
                "toDate": end_date,
            }

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()

            try:
                payload = response.json()
            except ValueError as error:
                raise RuntimeError(
                    "SSI API không trả về JSON."
                ) from error

            if payload.get("code") != "SUCCESS":
                raise RuntimeError(
                    "SSI API error: "
                    f"{payload.get('message')}"
                )

            records = payload.get("data") or []

            if not records:
                break

            all_records.extend(records)

            if len(records) < page_size:
                break

            page += 1

            # Không cho pagination chạy vô hạn
            if page > 100:
                raise RuntimeError(
                    "SSI API pagination vượt quá "
                    "100 trang."
                )

        if not all_records:
            return self._empty_dataframe()

        df = pd.DataFrame(all_records)

        required_columns = [
            "tradingDate",
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
                "SSI thiếu cột: "
                + ", ".join(missing_columns)
            )

        # ========================================================
        # DATE
        # ========================================================

        df["datetime"] = pd.to_datetime(
            df["tradingDate"],
            format="%d/%m/%Y",
            errors="coerce",
        )

        df = df.dropna(
            subset=["datetime"]
        )

        # ========================================================
        # NUMERIC
        # ========================================================

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
            subset=numeric_columns
        )

        # ========================================================
        # PRICE UNIT
        # ========================================================
        #
        # SSI:
        #   17,700 VND
        #
        # Project hiện tại:
        #   17.70 nghìn VND
        #
        # Chỉ chia giá, KHÔNG chia volume.
        # ========================================================

        price_columns = [
            "open",
            "high",
            "low",
            "close",
        ]

        for column in price_columns:
            df[column] = (
                df[column] / 1000.0
            )

        # ========================================================
        # TIMESTAMP
        # ========================================================

        df["timestamp"] = (
            df["datetime"]
            .astype("int64")
            // 10**9
        )

        # ========================================================
        # SYMBOL
        # ========================================================
        if "symbol" in df.columns:
            df["symbol"] = (
                df["symbol"]
                .fillna(symbol)
                .astype(str)
                .str.upper()
            )
        else:
            df.insert(
                0,
                "symbol",
                symbol,
            )
        # ========================================================
        # FINAL FORMAT
        # ========================================================

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
        ]

        df = (
            df
            .sort_values("datetime")
            .drop_duplicates(
                subset=["symbol", "datetime"],
                keep="last",
            )
            .reset_index(drop=True)
        )

        return df