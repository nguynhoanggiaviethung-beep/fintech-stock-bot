from bot.telegram_bot import build_stock_analysis


def main():

    symbol = "ABB"

    print("=" * 70)
    print(f"TEST BOT ANALYZE: {symbol}")
    print("=" * 70)

    result = build_stock_analysis(symbol)

    required_fields = [
        "symbol",
        "market_close",
        "market_volume",
        "realtime_price",
        "realtime_volume",
        "report_period",
        "revenue",
        "revenue_growth",
        "net_income",
        "net_income_growth",
        "eps",
        "roe",
        "debt_equity",
        "bvps",
        "pe",
        "pb",
        "market_cap",
        "signal",
        "fundamental_pass",
        "volume_breakout",
        "price_momentum",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing_fields:
        raise AssertionError(
            f"Missing fields: {missing_fields}"
        )

    valid_signals = [
        "BUY",
        "SELL",
        "NO_SIGNAL",
    ]

    if result["signal"] not in valid_signals:
        raise AssertionError(
            f"Invalid signal: {result['signal']}"
        )

    print("\nMARKET")
    print(
        f"Daily Close       : "
        f"{result['market_close']}"
    )
    print(
        f"Daily Volume      : "
        f"{result['market_volume']}"
    )

    print("\nREAL-TIME")
    print(
        f"Price             : "
        f"{result['realtime_price']}"
    )
    print(
        f"Volume            : "
        f"{result['realtime_volume']}"
    )
    print(
        f"Match Type        : "
        f"{result['realtime_match_type']}"
    )
    print(
        f"Time              : "
        f"{result['realtime_time']}"
    )

    print("\nFUNDAMENTAL")
    print(
        f"Report Period     : "
        f"{result['report_period']}"
    )
    print(
        f"Revenue           : "
        f"{result['revenue']}"
    )
    print(
        f"Revenue Growth    : "
        f"{result['revenue_growth']}"
    )
    print(
        f"Net Income        : "
        f"{result['net_income']}"
    )
    print(
        f"Net Income Growth : "
        f"{result['net_income_growth']}"
    )
    print(
        f"EPS               : "
        f"{result['eps']}"
    )
    print(
        f"ROE               : "
        f"{result['roe']}"
    )
    print(
        f"Debt/Equity       : "
        f"{result['debt_equity']}"
    )

    print("\nVALUATION")
    print(
        f"BVPS              : "
        f"{result['bvps']}"
    )
    print(
        f"P/E               : "
        f"{result['pe']}"
    )
    print(
        f"P/B               : "
        f"{result['pb']}"
    )
    print(
        f"Market Cap        : "
        f"{result['market_cap']}"
    )

    print("\nSIGNAL")
    print(
        f"Signal             : "
        f"{result['signal']}"
    )
    print(
        f"Fundamental Pass   : "
        f"{result['fundamental_pass']}"
    )
    print(
        f"Volume Breakout    : "
        f"{result['volume_breakout']}"
    )
    print(
        f"Price Momentum     : "
        f"{result['price_momentum']}"
    )

    print("\n" + "=" * 70)
    print("ALL BOT ANALYZE TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()