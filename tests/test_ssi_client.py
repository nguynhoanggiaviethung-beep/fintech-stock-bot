from datetime import datetime

from data.ssi_client import SSIDataClient


def main():
    client = SSIDataClient()

    df = client.get_historical_ohlcv(
        symbol="ABB",
        start_date="01/07/2026",
        end_date="18/09/2026",
    )

    print("\n===== SSI ABB TEST =====")
    print(df.head())
    print("\nRows:", len(df))

    if df.empty:
        raise AssertionError(
            "SSI không trả dữ liệu ABB."
        )

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

    for column in required_columns:
        if column not in df.columns:
            raise AssertionError(
                f"Thiếu cột: {column}"
            )

    if df["close"].isna().any():
        raise AssertionError(
            "close có giá trị NaN."
        )

    if df["volume"].isna().any():
        raise AssertionError(
            "volume có giá trị NaN."
        )

    if not (
        df["datetime"].is_monotonic_increasing
    ):
        raise AssertionError(
            "datetime không tăng dần."
        )

    if not (
        (df["close"] > 0).all()
    ):
        raise AssertionError(
            "close phải > 0."
        )

    print(
        "\nLatest:",
        df.iloc[-1].to_dict(),
    )

    print(
        "\nALL SSI TESTS PASSED"
    )


if __name__ == "__main__":
    main()