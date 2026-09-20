from analysis.trade_explanation import TradeExplanation


def test_buy_explanation():

    signal_result = {
        "symbol": "ABB",
        "signal": "BUY",

        "fundamental_pass": True,
        "volume_breakout": True,
        "price_momentum": True,

        "roe": 18.22,
        "revenue_growth": 89.47,
        "net_income_growth": 379.65,

        "volume_ratio": 2.50,
        "close": 12.87,
        "price_ma20": 11.95,

        "total_score": 100,
    }

    explanation = TradeExplanation()

    explained = explanation.explain(
        signal_result
    )

    assert explained["signal"] == "BUY"

    # Fundamental conditions
    assert (
        "Revenue Growth > 15%"
        in explained["reasons"]
    )

    assert (
        "Net Income Growth > 15%"
        in explained["reasons"]
    )

    assert (
        "ROE > 15%"
        in explained["reasons"]
    )

    # Technical conditions
    assert any(
        "Volume breakout"
        in reason
        for reason in explained["reasons"]
    )

    assert any(
        "Giá đóng cửa > MA20"
        in reason
        for reason in explained["reasons"]
    )

    # Formatted metrics
    assert (
        explained["formatted_metrics"]["ROE"]
        == "18.22%"
    )

    assert (
        explained["formatted_metrics"]["Revenue Growth"]
        == "89.47%"
    )

    assert (
        explained["formatted_metrics"]["Net Income Growth"]
        == "379.65%"
    )

    assert (
        explained["formatted_metrics"]["Volume Ratio"]
        == "2.50x"
    )

    assert (
        explained["formatted_metrics"]["Close"]
        == "12.87"
    )

    assert (
        explained["formatted_metrics"]["Price MA20"]
        == "11.95"
    )

    assert (
        explained["formatted_metrics"]["Price Momentum"]
        == "PASS"
    )

    assert (
        explained["formatted_metrics"]["Score"]
        == "100/100"
    )

    print(
        "\nBUY explanation:"
    )

    print(
        explanation.to_text(
            signal_result
        )
    )


def test_sell_explanation():

    signal_result = {
        "symbol": "ABB",
        "signal": "SELL",

        "price_break_ma20": True,
        "volume_reversal": False,

        "sell_reasons": [
            "Giá đóng cửa < MA20"
        ],

        "roe": 18.22,
        "revenue_growth": 89.47,
        "net_income_growth": 379.65,

        "volume_ratio": 1.20,

        "close": 11.50,
        "price_ma20": 12.00,

        "total_score": 100,
    }

    explanation = TradeExplanation()

    explained = explanation.explain(
        signal_result
    )

    assert explained["signal"] == "SELL"

    assert any(
        "Giá đóng cửa < MA20"
        in reason
        for reason in explained["reasons"]
    )

    print(
        "\nSELL explanation:"
    )

    print(
        explanation.to_text(
            signal_result
        )
    )


def test_no_signal_explanation():

    signal_result = {
        "symbol": "ACB",
        "signal": "NO_SIGNAL",

        "fundamental_pass": False,
        "volume_breakout": False,
        "price_momentum": False,

        "roe": 17.56,
        "revenue_growth": 0.84,
        "net_income_growth": -6.94,

        "volume_ratio": 1.20,

        "close": 25.00,
        "price_ma20": 25.50,

        "total_score": 30,
    }

    explanation = TradeExplanation()

    explained = explanation.explain(
        signal_result
    )

    assert (
        explained["signal"]
        == "NO_SIGNAL"
    )

    # Fundamental failure
    assert any(
        "Fundamental"
        in reason
        for reason in explained["reasons"]
    )

    # Volume failure
    assert any(
        "Volume"
        in reason
        for reason in explained["reasons"]
    )

    # Price momentum failure
    assert any(
        "Price Momentum"
        in reason
        for reason in explained["reasons"]
    )

    print(
        "\nNO_SIGNAL explanation:"
    )

    print(
        explanation.to_text(
            signal_result
        )
    )


if __name__ == "__main__":

    test_buy_explanation()
    test_sell_explanation()
    test_no_signal_explanation()

    print(
        "\n=========================================="
    )

    print(
        "ALL TRADE EXPLANATION TESTS PASSED"
    )

    print(
        "=========================================="
    )