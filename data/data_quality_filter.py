from __future__ import annotations

import pandas as pd


class DataQualityFilter:
    """
    Kiểm tra chất lượng dữ liệu trước khi đưa vào
    các bộ lọc đầu tư và Signal Engine.

    Data Quality Filter KHÔNG đánh giá cổ phiếu tốt/xấu.

    Nhiệm vụ:
        1. Kiểm tra market data
        2. Kiểm tra fundamental data
        3. Kiểm tra dữ liệu mới nhất
        4. Phát hiện missing / invalid values
        5. Kiểm tra đủ dữ liệu cho Volume MA20
    """

    REQUIRED_MARKET_COLUMNS = {
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    REQUIRED_FUNDAMENTAL_COLUMNS = {
        "symbol",
        "report_period",
        "revenue_growth",
        "net_income_growth",
        "roe",
    }

    def __init__(
        self,
        minimum_market_rows: int = 21,
    ):
        """
        minimum_market_rows = 21 vì Volume MA20 cần
        20 phiên trước + 1 phiên hiện tại.
        """

        self.minimum_market_rows = (
            minimum_market_rows
        )

    # ==================================================
    # MARKET DATA
    # ==================================================

    def validate_market_data(
        self,
        market_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra toàn bộ market DataFrame.
        """

        errors = []
        warnings = []

        if market_df is None:
            errors.append(
                "market_df is None"
            )

            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        if market_df.empty:
            errors.append(
                "Market data is empty"
            )

            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        # ----------------------------------------------
        # Required columns
        # ----------------------------------------------

        missing_columns = (
            self.REQUIRED_MARKET_COLUMNS
            - set(market_df.columns)
        )

        if missing_columns:
            errors.append(
                "Missing market columns: "
                f"{sorted(missing_columns)}"
            )

        if errors:
            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        # ----------------------------------------------
        # Minimum rows
        # ----------------------------------------------

        row_count = len(market_df)

        if row_count < self.minimum_market_rows:
            errors.append(
                "Not enough market data rows: "
                f"{row_count} < "
                f"{self.minimum_market_rows}"
            )

        # ----------------------------------------------
        # Datetime
        # ----------------------------------------------

        datetime_series = pd.to_datetime(
            market_df["datetime"],
            errors="coerce",
        )

        invalid_datetime = (
            datetime_series.isna().sum()
        )

        if invalid_datetime > 0:
            errors.append(
                "Invalid datetime values: "
                f"{invalid_datetime}"
            )

        # ----------------------------------------------
        # Numeric columns
        # ----------------------------------------------

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            numeric_series = pd.to_numeric(
                market_df[column],
                errors="coerce",
            )

            invalid_count = (
                numeric_series.isna().sum()
            )

            if invalid_count > 0:
                errors.append(
                    f"Invalid {column} values: "
                    f"{invalid_count}"
                )

        # ----------------------------------------------
        # Missing values
        # ----------------------------------------------

        missing_counts = (
            market_df[
                numeric_columns
            ]
            .isna()
            .sum()
        )

        for column, count in (
            missing_counts.items()
        ):
            if count > 0:
                errors.append(
                    f"Missing {column} values: "
                    f"{count}"
                )

        # ----------------------------------------------
        # Price validation
        # ----------------------------------------------

        close_values = pd.to_numeric(
            market_df["close"],
            errors="coerce",
        )

        if (
            close_values
            .notna()
            .any()
            and
            (close_values <= 0).any()
        ):
            errors.append(
                "Close price contains "
                "zero or negative values"
            )

        # ----------------------------------------------
        # Volume validation
        # ----------------------------------------------

        volume_values = pd.to_numeric(
            market_df["volume"],
            errors="coerce",
        )

        if (
            volume_values
            .notna()
            .any()
            and
            (volume_values < 0).any()
        ):
            errors.append(
                "Volume contains negative values"
            )

        # ----------------------------------------------
        # OHLC logical consistency
        # ----------------------------------------------

        open_values = pd.to_numeric(
            market_df["open"],
            errors="coerce",
        )

        high_values = pd.to_numeric(
            market_df["high"],
            errors="coerce",
        )

        low_values = pd.to_numeric(
            market_df["low"],
            errors="coerce",
        )

        if (
            high_values.notna().any()
            and low_values.notna().any()
        ):
            invalid_ohlc = (
                (high_values < low_values)
                | (high_values < open_values)
                | (high_values < close_values)
                | (low_values > open_values)
                | (low_values > close_values)
            )

            invalid_ohlc_count = (
                invalid_ohlc.fillna(False).sum()
            )

            if invalid_ohlc_count > 0:
                errors.append(
                    "Invalid OHLC relationships: "
                    f"{invalid_ohlc_count}"
                )

        # ----------------------------------------------
        # Duplicate timestamps
        # ----------------------------------------------

        duplicate_datetime_count = (
            datetime_series.duplicated().sum()
        )

        if duplicate_datetime_count > 0:
            warnings.append(
                "Duplicate datetime rows: "
                f"{duplicate_datetime_count}"
            )

        # ----------------------------------------------
        # Result
        # ----------------------------------------------

        return self._result(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=row_count,
        )

    # ==================================================
    # FUNDAMENTAL DATA
    # ==================================================

    def validate_fundamental_data(
        self,
        fundamental_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra fundamental DataFrame.
        """

        errors = []
        warnings = []

        if fundamental_df is None:
            errors.append(
                "fundamental_df is None"
            )

            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        if fundamental_df.empty:
            errors.append(
                "Fundamental data is empty"
            )

            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        # ----------------------------------------------
        # Required columns
        # ----------------------------------------------

        missing_columns = (
            self.REQUIRED_FUNDAMENTAL_COLUMNS
            - set(fundamental_df.columns)
        )

        if missing_columns:
            errors.append(
                "Missing fundamental columns: "
                f"{sorted(missing_columns)}"
            )

        if errors:
            return self._result(
                passed=False,
                errors=errors,
                warnings=warnings,
            )

        # ----------------------------------------------
        # Latest row
        # ----------------------------------------------

        latest = fundamental_df.iloc[0]

        # ----------------------------------------------
        # Required latest values
        # ----------------------------------------------

        required_numeric_columns = [
            "revenue_growth",
            "net_income_growth",
            "roe",
        ]

        for column in required_numeric_columns:
            value = pd.to_numeric(
                pd.Series([latest[column]]),
                errors="coerce",
            ).iloc[0]

            if pd.isna(value):
                errors.append(
                    f"Latest fundamental value "
                    f"{column} is missing or invalid"
                )

        # ----------------------------------------------
        # Report period
        # ----------------------------------------------

        report_period = latest[
            "report_period"
        ]

        if pd.isna(report_period):
            errors.append(
                "Latest report_period is missing"
            )

        # ----------------------------------------------
        # Symbol
        # ----------------------------------------------

        symbol = latest["symbol"]

        if (
            symbol is None
            or str(symbol).strip() == ""
        ):
            errors.append(
                "Latest fundamental symbol is empty"
            )

        # ----------------------------------------------
        # Result
        # ----------------------------------------------

        return self._result(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=len(fundamental_df),
        )

    # ==================================================
    # COMBINED VALIDATION
    # ==================================================

    def validate_stock_data(
        self,
        market_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra cả market data và fundamental data.
        """

        market_result = (
            self.validate_market_data(
                market_df
            )
        )

        fundamental_result = (
            self.validate_fundamental_data(
                fundamental_df
            )
        )

        passed = (
            market_result["passed"]
            and fundamental_result["passed"]
        )

        return {
            "passed": passed,
            "market": market_result,
            "fundamental": fundamental_result,
            "errors": (
                market_result["errors"]
                + fundamental_result["errors"]
            ),
            "warnings": (
                market_result["warnings"]
                + fundamental_result["warnings"]
            ),
        }

    # ==================================================
    # HELPERS
    # ==================================================

    @staticmethod
    def _result(
        passed: bool,
        errors: list[str],
        warnings: list[str],
        row_count: int | None = None,
    ) -> dict:
        return {
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "row_count": row_count,
        }