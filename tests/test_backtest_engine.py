import pandas as pd

from analysis.backtest_engine import BacktestEngine


def test_buy_then_sell_next_day_open():
    """
    BUY signal ngày 02/01
    -> thực hiện tại OPEN ngày 03/01 = 110

    SELL signal ngày 04/01
    -> thực hiện tại OPEN ngày 05/01 = 125
    """

    signals_df = pd.DataFrame(
        [
            {
                "datetime": "2026-01-01",
                "open": 100,
                "close": 101,
                "signal": "NO_SIGNAL",
            },
            {
                "datetime": "2026-01-02",
                "open": 102,
                "close": 105,
                "signal": "BUY",
            },
            {
                "datetime": "2026-01-03",
                "open": 110,
                "close": 115,
                "signal": "NO_SIGNAL",
            },
            {
                "datetime": "2026-01-04",
                "open": 118,
                "close": 120,
                "signal": "SELL",
            },
            {
                "datetime": "2026-01-05",
                "open": 125,
                "close": 123,
                "signal": "NO_SIGNAL",
            },
        ]
    )

    result = BacktestEngine().run(signals_df)

    assert result["total_trades"] == 1

    trade = result["trades"].iloc[0]

    assert trade["entry_price"] == 110
    assert trade["exit_price"] == 125

    expected_return = ((125 / 110) - 1) * 100

    assert abs(
        trade["return_pct"] - expected_return
    ) < 1e-9


def test_sell_without_position_is_ignored():
    signals_df = pd.DataFrame(
        [
            {
                "datetime": "2026-01-01",
                "open": 100,
                "close": 101,
                "signal": "SELL",
            },
            {
                "datetime": "2026-01-02",
                "open": 95,
                "close": 94,
                "signal": "NO_SIGNAL",
            },
        ]
    )

    result = BacktestEngine().run(signals_df)

    assert result["total_trades"] == 0
    assert result["final_capital"] == 100_000_000
    assert result["open_position"] is False


def test_buy_while_holding_is_ignored():
    signals_df = pd.DataFrame(
        [
            {
                "datetime": "2026-01-01",
                "open": 100,
                "close": 101,
                "signal": "BUY",
            },
            {
                "datetime": "2026-01-02",
                "open": 105,
                "close": 106,
                "signal": "BUY",
            },
            {
                "datetime": "2026-01-03",
                "open": 120,
                "close": 121,
                "signal": "SELL",
            },
            {
                "datetime": "2026-01-04",
                "open": 120,
                "close": 118,
                "signal": "NO_SIGNAL",
            },
        ]
    )

    result = BacktestEngine().run(signals_df)

    assert result["total_trades"] == 1

    trade = result["trades"].iloc[0]

    # BUY signal 01/01 -> BUY at OPEN 02/01 = 105
    assert trade["entry_price"] == 105

    # SELL signal 03/01 -> SELL at OPEN 04/01 = 120
    assert trade["exit_price"] == 120

    expected_return = ((120 / 105) - 1) * 100

    assert abs(
        trade["return_pct"] - expected_return
    ) < 1e-9


def test_last_day_signal_is_pending():
    """
    Nếu BUY xuất hiện ở ngày cuối cùng,
    không có ngày T+1 nên chưa được khớp.
    """

    signals_df = pd.DataFrame(
        [
            {
                "datetime": "2026-01-01",
                "open": 100,
                "close": 101,
                "signal": "NO_SIGNAL",
            },
            {
                "datetime": "2026-01-02",
                "open": 105,
                "close": 110,
                "signal": "BUY",
            },
        ]
    )

    result = BacktestEngine().run(signals_df)

    assert result["total_trades"] == 0
    assert result["open_position"] is False
    assert result["pending_action"] == "BUY"

def test_mark_to_market_max_drawdown():
    """
    Kiểm tra Maximum Drawdown trên daily mark-to-market equity.

    BUY signal ngày 02/01
    -> BUY tại OPEN ngày 03/01 = 100

    CLOSE ngày 03/01 = 90
    -> unrealized loss = -10%

    SELL signal ngày 04/01
    -> SELL tại OPEN ngày 05/01 = 100

    MDD phải phản ánh mức giảm 100 -> 90,
    tức khoảng -10%.
    """

    signals_df = pd.DataFrame(
        [
            {
                "datetime": "2026-01-01",
                "open": 100,
                "close": 100,
                "signal": "NO_SIGNAL",
            },
            {
                "datetime": "2026-01-02",
                "open": 100,
                "close": 100,
                "signal": "BUY",
            },
            {
                "datetime": "2026-01-03",
                "open": 100,
                "close": 90,
                "signal": "NO_SIGNAL",
            },
            {
                "datetime": "2026-01-04",
                "open": 90,
                "close": 90,
                "signal": "SELL",
            },
            {
                "datetime": "2026-01-05",
                "open": 100,
                "close": 100,
                "signal": "NO_SIGNAL",
            },
        ]
    )

    result = BacktestEngine().run(
        signals_df
    )

    assert result["total_trades"] == 1

    assert abs(
        result["max_drawdown"] - (-10.0)
    ) < 1e-9

if __name__ == "__main__":
    test_buy_then_sell_next_day_open()
    test_sell_without_position_is_ignored()
    test_buy_while_holding_is_ignored()
    test_last_day_signal_is_pending()
    test_mark_to_market_max_drawdown()

    print("ALL BACKTEST ENGINE TESTS PASSED")