from __future__ import annotations

from datetime import datetime, timedelta

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

        # ========================================================
        # DATE RANGE
        # ========================================================
        #
        # SSI có giới hạn số dữ liệu trả về trong một khoảng
        # thời gian lớn.
        #
        # Vì vậy khoảng thời gian được chia thành từng đoạn
        # nhỏ rồi gọi SSI nhiều lần.
        #
        # Ví dụ:
        #   2021 -> 2026
        #
        # sẽ được chia thành:
        #   2021 -> 2022
        #   2022 -> 2023
        #   ...
        #
        # Các đoạn có overlap 1 ngày để tránh bỏ sót dữ liệu.
        # Sau đó sẽ drop_duplicates theo symbol + datetime.
        # ========================================================

        requested_start = datetime.strptime(
            start_date,
            "%d/%m/%Y",
        )

        requested_end = datetime.strptime(
            end_date,
            "%d/%m/%Y",
        )

        if requested_start > requested_end:
            raise ValueError(
                "start_date phải nhỏ hơn hoặc bằng end_date."
            )

        # Chia nhỏ mỗi request tối đa khoảng 90 ngày.
        chunk_days = 90

        all_records = []

        chunk_start = requested_start

        while chunk_start <= requested_end:

            chunk_end = min(
                chunk_start
                + timedelta(days=chunk_days - 1),
                requested_end,
            )

            chunk_start_str = chunk_start.strftime(
                "%d/%m/%Y"
            )

            chunk_end_str = chunk_end.strftime(
                "%d/%m/%Y"
            )

            print(
                f"[SSI] {symbol}: "
                f"{chunk_start_str} -> {chunk_end_str}",
                flush=True,
            )

            page = 1

            while True:

                params = {
                    "symbol": symbol,
                    "page": page,
                    "pageSize": page_size,
                    "fromDate": chunk_start_str,
                    "toDate": chunk_end_str,
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

            # Overlap 1 ngày giữa hai chunk.
            # Ví dụ chunk trước kết thúc 29/09,
            # chunk sau bắt đầu 29/09.
            #
            # Dữ liệu trùng sẽ được loại ở cuối hàm.
            chunk_start = (
                chunk_end
                - timedelta(days=1)
            )

            # Tránh vòng lặp vô hạn khi đã tới ngày cuối.
            if chunk_end >= requested_end:
                break

        # ========================================================
        # EMPTY RESULT
        # ========================================================

        if not all_records:
            return self._empty_dataframe()

        df = pd.DataFrame(
            all_records
        )

        # ========================================================
        # REQUIRED COLUMNS
        # ========================================================

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
                subset=[
                    "symbol",
                    "datetime",
                ],
                keep="last",
            )
            .reset_index(drop=True)
        )

        # Chỉ giữ dữ liệu nằm trong khoảng user yêu cầu.
        df = df[
            (df["datetime"] >= requested_start)
            & (df["datetime"] <= requested_end)
        ].reset_index(drop=True)

        return df