import pandas as pd


class MarketDataValidator:
    REQUIRED_COLUMNS = [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    @classmethod
    def validate_ohlcv(cls, df):
        errors = []

        # 1. Required columns
        missing_columns = [
            column
            for column in cls.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            errors.append(
                f"Missing columns: {missing_columns}"
            )

        if errors:
            return False, errors

        # 2. Empty data
        if df.empty:
            errors.append("DataFrame is empty")
            return False, errors

        # 3. Missing values
        for column in cls.REQUIRED_COLUMNS:
            if df[column].isna().any():
                errors.append(
                    f"Missing values in column: {column}"
                )

        # 4. Numeric validation
        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:
            if not pd.api.types.is_numeric_dtype(df[column]):
                errors.append(
                    f"Column '{column}' is not numeric"
                )

        # 5. Price > 0
        for column in ["open", "high", "low", "close"]:
            if (df[column] <= 0).any():
                errors.append(
                    f"Invalid non-positive price in '{column}'"
                )

        # 6. Volume >= 0
        if (df["volume"] < 0).any():
            errors.append("Negative volume detected")

        # 7. High >= Low
        if (df["high"] < df["low"]).any():
            errors.append("High < Low detected")

        # 8. High >= Open
        if (df["high"] < df["open"]).any():
            errors.append("High < Open detected")

        # 9. High >= Close
        if (df["high"] < df["close"]).any():
            errors.append("High < Close detected")

        # 10. Low <= Open
        if (df["low"] > df["open"]).any():
            errors.append("Low > Open detected")

        # 11. Low <= Close
        if (df["low"] > df["close"]).any():
            errors.append("Low > Close detected")

        # 12. Duplicate timestamps
        if df["timestamp"].duplicated().any():
            errors.append("Duplicate timestamps detected")

        # 13. Chronological order
        if not df["timestamp"].is_monotonic_increasing:
            errors.append(
                "Timestamps are not in ascending order"
            )

        return len(errors) == 0, errors