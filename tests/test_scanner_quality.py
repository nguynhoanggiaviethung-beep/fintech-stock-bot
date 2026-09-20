from analysis.stock_scanner import StockScanner


def main():

    scanner = StockScanner(
        lookback_days=90,
        request_delay=0.2,
    )

    symbols = [
        "ABB",
        "ABC",
        "ACB",
        "FPT",
        "HVG",
    ]

    results, statistics = (
        scanner.scan_symbols(
            symbols
        )
    )

    scanner.print_statistics(
        statistics
    )

    print()

    print(
        "RESULTS"
    )

    for result in results:

        print(
            result
        )


if __name__ == "__main__":
    main()