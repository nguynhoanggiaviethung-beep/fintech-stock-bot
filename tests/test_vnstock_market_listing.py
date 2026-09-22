from vnstock import Listing


def main():
    listing = Listing()

    print("\n===== VNSTOCK MARKET LISTING TEST =====")

    df = listing.all_symbols()

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nRows:", len(df))

    print("\nHead:")
    print(df.head(10).to_string(index=False))

    print("\nSample symbols:")
    print(
        df[
            df["symbol"].isin(
                ["A32", "AAA", "ACB", "FPT", "VCB"]
            )
        ].to_string(index=False)
    )

    if df.empty:
        raise AssertionError(
            "VNStock không trả danh sách cổ phiếu."
        )

    if "symbol" not in df.columns:
        raise AssertionError(
            "VNStock listing thiếu cột symbol."
        )

    print(
        "\nALL VNSTOCK MARKET LISTING TESTS PASSED"
    )


if __name__ == "__main__":
    main()