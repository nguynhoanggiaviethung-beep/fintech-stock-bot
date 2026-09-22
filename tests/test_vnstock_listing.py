from vnstock import Listing


def main():
    print("\n===== VNSTOCK LISTING TEST =====")

    listing = Listing()

    df = listing.all_symbols()

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nRows:", len(df))

    print("\nHead:")
    print(df.head())

    if df.empty:
        raise AssertionError(
            "VNStock không trả danh sách cổ phiếu."
        )

    if "symbol" not in df.columns:
        raise AssertionError(
            "VNStock listing thiếu cột symbol."
        )

    print(
        "\nALL VNSTOCK LISTING TESTS PASSED"
    )


if __name__ == "__main__":
    main()