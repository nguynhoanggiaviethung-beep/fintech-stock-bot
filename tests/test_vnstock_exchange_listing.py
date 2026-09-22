from vnstock import Listing


def main():
    listing = Listing()

    print("\n===== VNSTOCK EXCHANGE LISTING TEST =====")

    exchanges = ["HOSE", "HNX", "UPCOM"]

    all_results = {}

    for exchange in exchanges:
        print(f"\n--- {exchange} ---")

        try:
            df = listing.symbols_by_exchange(exchange)

            all_results[exchange] = df

            print("Columns:")
            print(df.columns.tolist())

            print("Rows:", len(df))

            print("\nHead:")
            print(
                df.head(5).to_string(
                    index=False
                )
            )

        except Exception as error:
            print(
                f"ERROR {exchange}: "
                f"{type(error).__name__}: {error}"
            )

    print("\n===== SUMMARY =====")

    for exchange, df in all_results.items():
        if df is not None:
            print(
                f"{exchange}: {len(df)} rows"
            )

    successful = [
        exchange
        for exchange, df in all_results.items()
        if df is not None and not df.empty
    ]

    if not successful:
        raise AssertionError(
            "VNStock không trả được danh sách "
            "cổ phiếu theo sàn."
        )

    print(
        "\nALL VNSTOCK EXCHANGE LISTING "
        "TESTS PASSED"
    )


if __name__ == "__main__":
    main()