from __future__ import annotations

import pandas as pd

from analysis.exit_filter import ExitFilter


def build_market_data(
    closes,
    volumes=None,
):
    if volumes is None:
        volumes = [1000] * len(closes)

    dates = pd.date_range(
        start="2026-01-01",
        periods=len(closes),
        freq="D",
    )

    return pd.DataFrame(
        {
            "datetime": dates,
            "close": closes,
            "volume": volumes,
        }
    )


def test_price_break_ma20():
    closes = [100] * 20 + [90]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
    )

    print("\nPRICE BREAK MA20")
    print(result)

    assert result["price_break_ma20"] is True
    assert result["sell_trigger"] is True
    assert result["sell_signal"] is True


def test_volume_reversal():
    closes = [100] * 20 + [95]

    volumes = [1000] * 20 + [2000]

    df = build_market_data(
        closes=closes,
        volumes=volumes,
    )

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
    )

    print("\nVOLUME REVERSAL")
    print(result)

    assert result["volume_ratio"] == 2.0
    assert result["volume_reversal"] is True
    assert result["sell_trigger"] is True
    assert result["sell_signal"] is True


def test_stop_loss():
    """
    Entry = 100
    Close = 95
    Loss = -5%

    Stop Loss threshold = 5%
    => Stop Loss must trigger.
    """

    closes = [100] * 20 + [95]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
        entry_price=100,
        highest_price=100,
    )

    print("\nSTOP LOSS")
    print(result)

    assert result["entry_price"] == 100
    assert result["loss_pct"] == -5.0
    assert result["stop_loss_trigger"] is True
    assert result["sell_trigger"] is True
    assert result["sell_signal"] is True


def test_stop_loss_not_holding():
    """
    Có entry_price nhưng không HOLDING
    => Stop Loss không được kích hoạt.
    """

    closes = [100] * 20 + [95]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=False,
        entry_price=100,
        highest_price=100,
    )

    print("\nSTOP LOSS - NOT HOLDING")
    print(result)

    assert result["loss_pct"] is None
    assert result["stop_loss_trigger"] is False
    assert result["sell_signal"] is False


def test_trailing_stop():
    """
    Entry = 100
    Highest price since BUY = 120
    Trailing Stop = 120 * 95% = 114
    Close = 113

    => Trailing Stop must trigger.
    """

    closes = [100] * 20 + [113]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
        entry_price=100,
        highest_price=120,
    )

    print("\nTRAILING STOP")
    print(result)

    assert result["trailing_stop_price"] == 114.0
    assert result["trailing_stop_trigger"] is True
    assert result["sell_trigger"] is True
    assert result["sell_signal"] is True


def test_trailing_stop_not_triggered():
    """
    Entry = 100
    Highest price = 120
    Trailing Stop = 114

    Close = 115
    => Chưa chạm Trailing Stop.
    """

    closes = [100] * 20 + [115]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
        entry_price=100,
        highest_price=120,
    )

    print("\nTRAILING STOP - NOT TRIGGERED")
    print(result)

    assert result["trailing_stop_price"] == 114.0
    assert result["trailing_stop_trigger"] is False
    assert result["sell_signal"] is False


def test_trailing_stop_not_holding():
    """
    Không HOLDING
    => Trailing Stop không được kích hoạt.
    """

    closes = [100] * 20 + [110]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=False,
        entry_price=100,
        highest_price=120,
    )

    print("\nTRAILING STOP - NOT HOLDING")
    print(result)

    assert result["trailing_stop_price"] is None
    assert result["trailing_stop_trigger"] is False
    assert result["sell_signal"] is False


def test_no_sell():
    """
    Không có điều kiện SELL.
    """

    closes = [100] * 21

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=True,
        entry_price=100,
        highest_price=100,
    )

    print("\nNO SELL")
    print(result)

    assert result["stop_loss_trigger"] is False
    assert result["trailing_stop_trigger"] is False
    assert result["price_break_ma20"] is False
    assert result["volume_reversal"] is False
    assert result["sell_trigger"] is False
    assert result["sell_signal"] is False


def test_not_holding():
    """
    Có điều kiện kỹ thuật nhưng không HOLDING
    => không phát SELL signal.
    """

    closes = [100] * 20 + [90]

    df = build_market_data(closes)

    exit_filter = ExitFilter(
        price_window=20,
        volume_window=20,
        volume_breakout_ratio=1.5,
        stop_loss_pct=5.0,
        trailing_stop_pct=5.0,
    )

    result = exit_filter.check_latest(
        market_df=df,
        position_held=False,
    )

    print("\nNOT HOLDING")
    print(result)

    assert result["sell_signal"] is False


if __name__ == "__main__":
    test_price_break_ma20()
    test_volume_reversal()
    test_stop_loss()
    test_stop_loss_not_holding()
    test_trailing_stop()
    test_trailing_stop_not_triggered()
    test_trailing_stop_not_holding()
    test_no_sell()
    test_not_holding()

    print("\nALL EXIT FILTER TESTS PASSED")