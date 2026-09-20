import pandas as pd

from analysis.backtest_runner import BacktestRunner


def create_fundamental_data():

    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "revenue": 8_565_277_000_000,
                "revenue_growth": 89.47,
                "net_income": 2_808_626_000_000,
                "net_income_growth": 379.65,
                "eps": 2714,
                "roe": 18.22,
                "debt_equity": 12.12,
                "pe": None,
                "pb": None,
            }
        ]
    )


def create_market_data():

    dates = pd.date_range(
        "2026-04-01",
        periods=25,
        freq="D",
    )

    rows = []

    for i, date in enumerate(dates):

        rows.append(
            {
                "datetime": date,
                "open": 12.0 + i * 0.1,
                "high": 12.2 + i * 0.1,
                "low": 11.8 + i * 0.1,
                "close": 12.1 + i * 0.1,
                "volume": 100_000,
            }
        )

    df = pd.DataFrame(rows)

    # Tạo volume breakout ở cuối chuỗi
    df.loc[
        df.index[-1],
        "volume",
    ] = 200_000

    return df


def test_backtest_runner_has_explanation():

    fundamental_df = (
        create_fundamental_data()
    )

    market_df = (
        create_market_data()
    )

    runner = BacktestRunner()

    result = runner.run(
        fundamental_df=fundamental_df,
        market_df=market_df,
    )

    signals_df = result["signals"]

    assert not signals_df.empty

    assert (
        "explanation_summary"
        in signals_df.columns
    )

    assert (
        "explanation_reasons"
        in signals_df.columns
    )

    assert (
        "explanation_metrics"
        in signals_df.columns
    )

    assert (
        "explanation_text"
        in signals_df.columns
    )

    # Kiểm tra explanation có thực sự được tạo
    assert (
        signals_df[
            "explanation_summary"
        ]
        .notna()
        .all()
    )

    assert (
        signals_df[
            "explanation_text"
        ]
        .notna()
        .all()
    )

    print("\nEXPLANATION SAMPLE")
    print("=" * 70)

    sample = signals_df.iloc[-1]

    print(
        sample[
            [
                "datetime",
                "signal",
                "explanation_summary",
                "explanation_reasons",
            ]
        ].to_string()
    )

    print("\nFULL EXPLANATION")
    print("=" * 70)

    print(
        sample[
            "explanation_text"
        ]
    )


if __name__ == "__main__":

    test_backtest_runner_has_explanation()

    print(
        "\nALL BACKTEST EXPLANATION TESTS PASSED"
    )