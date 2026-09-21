from data.market_scanner import MarketScanner


def main():
    scanner = MarketScanner(
        request_delay=0.2
    )

    print("=" * 60)
    print("TEST MARKET SCANNER")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Lấy universe
    # --------------------------------------------------------

    print("\n[1] Lấy danh sách cổ phiếu...")

    universe = scanner.get_stock_universe()

    print(
        f"Universe: {len(universe)} mã"
    )

    print("\n5 mã đầu tiên:")
    print(
        universe.head(5).to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 2. Kiểm tra đủ 3 sàn
    # --------------------------------------------------------

    print("\n[2] Kiểm tra các sàn...")

    print(
        universe["market"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # 3. Chỉ test 5 mã
    # --------------------------------------------------------

    test_universe = universe.head(5)

    print(
        "\n[3] Quét thử 5 mã..."
    )

    result = scanner.scan_market(
        universe=test_universe
    )

    # --------------------------------------------------------
    # 4. Hiển thị kết quả
    # --------------------------------------------------------

    print("\n[4] Kết quả:")

    if result.empty:
        raise AssertionError(
            "Không lấy được dữ liệu của mã nào."
        )

    print(
        result.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 5. Kiểm tra columns
    # --------------------------------------------------------

    required_columns = {
        "symbol",
        "market",
        "close",
        "previous_close",
        "change_pct",
        "volume",
    }

    missing = (
        required_columns
        - set(result.columns)
    )

    if missing:
        raise AssertionError(
            f"Thiếu columns: {missing}"
        )

    # --------------------------------------------------------
    # 6. Test breadth
    # --------------------------------------------------------

    print(
        "\n[5] Market breadth:"
    )

    breadth = scanner.market_breadth(
        result
    )

    print(breadth)

    assert (
        breadth["total"]
        == len(result)
    )

    # --------------------------------------------------------
    # 7. Test top gainers
    # --------------------------------------------------------

    print(
        "\n[6] Top gainers:"
    )

    gainers = scanner.top_gainers(
        result,
        n=5,
    )

    if not gainers.empty:
        print(
            gainers[
                [
                    "symbol",
                    "market",
                    "close",
                    "change_pct",
                    "volume",
                ]
            ].to_string(
                index=False
            )
        )
    else:
        print(
            "Không có mã tăng trong 5 mã test."
        )

    # --------------------------------------------------------
    # 8. Test top losers
    # --------------------------------------------------------

    print(
        "\n[7] Top losers:"
    )

    losers = scanner.top_losers(
        result,
        n=5,
    )

    if not losers.empty:
        print(
            losers[
                [
                    "symbol",
                    "market",
                    "close",
                    "change_pct",
                    "volume",
                ]
            ].to_string(
                index=False
            )
        )
    else:
        print(
            "Không có mã giảm trong 5 mã test."
        )

    # --------------------------------------------------------
    # 9. Test breadth theo sàn
    # --------------------------------------------------------

    print(
        "\n[8] Breadth theo sàn:"
    )

    breadth_by_market = (
        scanner.breadth_by_market(
            result
        )
    )

    if not breadth_by_market.empty:
        print(
            breadth_by_market.to_string(
                index=False
            )
        )

    print("\n" + "=" * 60)
    print(
        "ALL MARKET SCANNER TESTS PASSED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()