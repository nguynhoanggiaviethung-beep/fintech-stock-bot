import pandas as pd

from analysis.backtest_runner import BacktestRunner


class FakeSignalEngine:
    """
    Signal Engine giả lập để test BacktestRunner.

    Logic:
    - Ngày có volume >= 2000 và chưa HOLDING -> BUY
    - Khi HOLDING và giá đóng cửa < 95 -> SELL
    - Còn lại -> NO_SIGNAL

    Fake engine nhận highest_price để kiểm tra
    BacktestRunner có truyền đúng trạng thái trailing stop hay không.
    """

    def analyze(
        self,
        fundamental_df,
        market_df,
        symbol="UNKNOWN",
        position_held=False,
        entry_price=None,
        highest_price=None,
    ):
        latest = market_df.iloc[-1]

        close = float(latest["close"])
        volume = float(latest["volume"])

        if volume >= 2000 and not position_held:
            signal = "BUY"

        elif close < 95 and position_held:
            signal = "SELL"

        else:
            signal = "NO_SIGNAL"

        return {
            "symbol": symbol,
            "signal": signal,
            "buy_signal": signal == "BUY",
            "sell_signal": signal == "SELL",
            "score": 100 if signal == "BUY" else 0,
            "entry_price": entry_price,
            "highest_price": highest_price,
        }


def create_test_data():
    """
    Tạo OHLCV test data dùng chung.
    """

    market_df = pd.DataFrame(
        [
            {
                "datetime": "2026-08-01",
                "open": 100,
                "close": 100,
                "volume": 1000,
            },
            {
                "datetime": "2026-08-02",
                "open": 100,
                "close": 100,
                "volume": 1000,
            },
            {
                "datetime": "2026-08-03",
                "open": 110,
                "close": 110,
                "volume": 2000,
            },
            {
                "datetime": "2026-08-04",
                "open": 112,
                "close": 112,
                "volume": 1000,
            },
            {
                "datetime": "2026-08-05",
                "open": 105,
                "close": 90,
                "volume": 1000,
            },
            {
                "datetime": "2026-08-06",
                "open": 88,
                "close": 88,
                "volume": 1000,
            },
        ]
    )

    fundamental_df = pd.DataFrame(
        [
            {
                "symbol": "TEST",
                "roe": 20,
                "revenue_growth": 20,
                "net_income_growth": 20,
            }
        ]
    )

    return market_df, fundamental_df


def test_generate_signals():

    market_df, fundamental_df = create_test_data()

    runner = BacktestRunner(
        signal_engine=FakeSignalEngine()
    )

    signals_df = runner.generate_signals(
        fundamental_df=fundamental_df,
        market_df=market_df,
    )

    assert len(signals_df) == 6

    # --------------------------------------------------
    # BUY SIGNAL
    # --------------------------------------------------

    # BUY signal phát sinh ngày 03/08.
    assert (
        signals_df.loc[2, "signal"]
        == "BUY"
    )

    # --------------------------------------------------
    # SELL SIGNAL
    # --------------------------------------------------

    # SELL signal phát sinh ngày 05/08.
    assert (
        signals_df.loc[4, "signal"]
        == "SELL"
    )

    # --------------------------------------------------
    # OHLC
    # --------------------------------------------------

    assert "open" in signals_df.columns
    assert "close" in signals_df.columns

    # --------------------------------------------------
    # ENTRY PRICE
    # --------------------------------------------------

    # Ngày 03/08 mới phát BUY signal.
    # Chưa được execution nên chưa có entry_price.
    assert pd.isna(
        signals_df.loc[2, "entry_price"]
    )

    # Ngày 04/08:
    # BUY được execution tại OPEN = 112.
    assert (
        signals_df.loc[3, "executed_action"]
        == "BUY"
    )

    assert (
        signals_df.loc[3, "entry_price"]
        == 112
    )

    # Ngày 05/08:
    # vẫn đang HOLDING.
    # entry_price phải tiếp tục là 112.
    assert (
        signals_df.loc[4, "entry_price"]
        == 112
    )

    # SELL ngày 05/08 mới chỉ là signal,
    # chưa execution.
    assert (
        bool(
            signals_df.loc[
                4,
                "position_after_execution",
            ]
        )
        is True
    )

    # --------------------------------------------------
    # HIGHEST PRICE
    # --------------------------------------------------

    # Sau BUY execution ngày 04/08:
    # entry_price = 112
    # close ngày 04/08 = 112
    # highest_price = 112.
    assert (
        signals_df.loc[3, "highest_price"]
        == 112
    )

    # Ngày 05/08:
    # close = 90, thấp hơn highest_price 112.
    # highest_price phải vẫn giữ 112.
    assert (
        signals_df.loc[4, "highest_price"]
        == 112
    )


def test_runner_backtest_uses_next_day_open():

    market_df, fundamental_df = create_test_data()

    runner = BacktestRunner(
        signal_engine=FakeSignalEngine()
    )

    result = runner.run(
        fundamental_df=fundamental_df,
        market_df=market_df,
    )

    signals_df = result["signals"]

    backtest = result["backtest"]

    # --------------------------------------------------
    # TRADE COUNT
    # --------------------------------------------------

    assert backtest["total_trades"] == 1

    trade = backtest["trades"].iloc[0]

    # --------------------------------------------------
    # ENTRY
    # --------------------------------------------------

    # BUY signal 03/08
    # => khớp OPEN 04/08 = 112
    assert trade["entry_price"] == 112

    # --------------------------------------------------
    # EXIT
    # --------------------------------------------------

    # SELL signal 05/08
    # => khớp OPEN 06/08 = 88
    assert trade["exit_price"] == 88

    # --------------------------------------------------
    # RETURN
    # --------------------------------------------------

    expected_return = (
        (88 / 112) - 1
    ) * 100

    assert abs(
        trade["return_pct"] - expected_return
    ) < 1e-9

    # --------------------------------------------------
    # ENTRY PRICE PIPELINE
    # --------------------------------------------------

    # Trước BUY execution:
    # entry_price chưa tồn tại.
    assert pd.isna(
        signals_df.loc[2, "entry_price"]
    )

    # BUY execution tại OPEN 04/08.
    assert (
        signals_df.loc[3, "executed_action"]
        == "BUY"
    )

    assert (
        signals_df.loc[3, "entry_price"]
        == 112
    )

    # --------------------------------------------------
    # HOLDING
    # --------------------------------------------------

    # Ngày 05/08:
    # SELL signal xuất hiện nhưng chưa execution.
    assert (
        signals_df.loc[4, "signal"]
        == "SELL"
    )

    # Giá mua vẫn được giữ.
    assert (
        signals_df.loc[4, "entry_price"]
        == 112
    )

    assert (
        bool(
            signals_df.loc[
                4,
                "position_after_execution",
            ]
        )
        is True
    )

    # --------------------------------------------------
    # HIGHEST PRICE PIPELINE
    # --------------------------------------------------

    # Sau BUY execution:
    # highest_price bắt đầu từ entry_price.
    assert (
        signals_df.loc[3, "highest_price"]
        == 112
    )

    # Giá đóng cửa ngày 05/08 = 90,
    # nhưng highest_price không được giảm theo giá hiện tại.
    assert (
        signals_df.loc[4, "highest_price"]
        == 112
    )

    # --------------------------------------------------
    # SELL EXECUTION
    # --------------------------------------------------

    # SELL được execution tại OPEN 06/08.
    assert (
        signals_df.loc[5, "executed_action"]
        == "SELL"
    )

    # Sau SELL không còn entry_price.
    assert pd.isna(
        signals_df.loc[5, "entry_price"]
    )

    # Sau SELL không còn position.
    assert (
        bool(
            signals_df.loc[
                5,
                "position_after_execution",
            ]
        )
        is False
    )

    # Sau SELL phải reset highest_price.
    assert pd.isna(
        signals_df.loc[5, "highest_price"]
    )


if __name__ == "__main__":
    test_generate_signals()
    test_runner_backtest_uses_next_day_open()

    print("ALL BACKTEST RUNNER TESTS PASSED")