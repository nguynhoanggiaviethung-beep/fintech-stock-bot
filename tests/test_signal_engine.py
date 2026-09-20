from __future__ import annotations

import pandas as pd

from analysis.signal_engine import SignalEngine


def create_fundamental_data():
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "roe": 18.0,
                "revenue_growth": 20.0,
                "net_income_growth": 25.0,
            }
        ]
    )


def create_market_data(
    last_close: float,
    last_volume: float,
):
    dates = pd.date_range(
        "2026-08-01",
        periods=21,
        freq="D",
    )

    closes = [100.0] * 20
    closes.append(last_close)

    volumes = [1000] * 20
    volumes.append(last_volume)

    return pd.DataFrame(
        {
            "symbol": ["ABB"] * 21,
            "datetime": dates,
            "close": closes,
            "volume": volumes,
        }
    )


# ==========================================================
# SELL TESTS
# ==========================================================


def test_holding_and_price_break_ma20():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    market_df = create_market_data(
        last_close=90,
        last_volume=1000,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=True,
    )

    print("\nHOLDING + PRICE BREAK MA20")
    print(result)

    assert result["position_held"] is True
    assert result["sell_signal"] is True
    assert result["price_break_ma20"] is True
    assert result["signal"] == "SELL"


def test_not_holding():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    market_df = create_market_data(
        last_close=90,
        last_volume=1000,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=False,
    )

    print("\nNOT HOLDING")
    print(result)

    assert result["position_held"] is False
    assert result["sell_trigger"] is True
    assert result["sell_signal"] is False
    assert result["signal"] != "SELL"


def test_holding_without_exit_condition():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    market_df = create_market_data(
        last_close=100,
        last_volume=1000,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=True,
    )

    print("\nHOLDING + NO EXIT CONDITION")
    print(result)

    assert result["position_held"] is True
    assert result["sell_signal"] is False
    assert result["signal"] != "SELL"


# ==========================================================
# BUY TESTS
# ==========================================================


def test_buy_all_conditions_pass():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    # Fundamental:
    # Revenue Growth = 20% > 15%
    # Net Income Growth = 25% > 15%
    # ROE = 18% > 15%
    #
    # Technical:
    # Volume = 1600
    # Volume MA20 = 1000
    # Volume Ratio = 1.6 >= 1.5
    #
    # Close = 101
    # Price MA20 = 100.05
    # Close > MA20
    #
    # => BUY

    market_df = create_market_data(
        last_close=101,
        last_volume=1600,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=False,
    )

    print("\nBUY - ALL CONDITIONS PASS")
    print(result)

    assert result["position_held"] is False

    assert result["fundamental_pass"] is True

    assert result["volume_breakout"] is True
    assert result["price_momentum"] is True

    assert result["buy_signal"] is True
    assert result["signal"] == "BUY"


def test_buy_blocked_when_price_momentum_fails():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    # Fundamental PASS
    #
    # Volume:
    # 1600 / 1000 = 1.6
    # => Volume Breakout PASS
    #
    # Price:
    # 20 phiên trước = 100
    # phiên cuối = 99
    #
    # MA20 = (19*100 + 99) / 20
    #      = 99.95
    #
    # 99 < 99.95
    # => Price Momentum FAIL
    #
    # => Không được BUY

    market_df = create_market_data(
        last_close=99,
        last_volume=1600,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=False,
    )

    print("\nBUY BLOCKED - PRICE MOMENTUM FAIL")
    print(result)

    assert result["fundamental_pass"] is True
    assert result["volume_breakout"] is True
    assert result["price_momentum"] is False

    assert result["buy_signal"] is False
    assert result["signal"] == "NO_SIGNAL"


def test_buy_blocked_when_volume_breakout_fails():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    # Price Momentum PASS:
    #
    # Close = 101
    # MA20 = 100.05
    # => PASS
    #
    # Volume:
    # 1000 / 1000 = 1.0
    # => Volume Breakout FAIL
    #
    # => Không được BUY

    market_df = create_market_data(
        last_close=101,
        last_volume=1000,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=False,
    )

    print("\nBUY BLOCKED - VOLUME BREAKOUT FAIL")
    print(result)

    assert result["fundamental_pass"] is True
    assert result["volume_breakout"] is False
    assert result["price_momentum"] is True

    assert result["buy_signal"] is False
    assert result["signal"] == "NO_SIGNAL"


def test_buy_blocked_when_fundamental_fails():

    engine = SignalEngine()

    # Fundamental không đạt:
    # Revenue Growth = 10%
    # Net Income Growth = 12%
    # ROE = 14%
    #
    # Technical đều đạt:
    # Volume Breakout = True
    # Price Momentum = True
    #
    # => Vẫn không được BUY

    fundamental_df = pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "roe": 14.0,
                "revenue_growth": 10.0,
                "net_income_growth": 12.0,
            }
        ]
    )

    market_df = create_market_data(
        last_close=101,
        last_volume=1600,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=False,
    )

    print("\nBUY BLOCKED - FUNDAMENTAL FAIL")
    print(result)

    assert result["fundamental_pass"] is False
    assert result["volume_breakout"] is True
    assert result["price_momentum"] is True

    assert result["buy_signal"] is False
    assert result["signal"] == "NO_SIGNAL"


def test_buy_blocked_when_already_holding():

    engine = SignalEngine()

    fundamental_df = create_fundamental_data()

    # Tất cả điều kiện BUY đều đạt.
    #
    # Nhưng position_held = True
    # => Không được tạo BUY thứ hai.

    market_df = create_market_data(
        last_close=101,
        last_volume=1600,
    )

    result = engine.analyze(
        fundamental_df=fundamental_df,
        market_df=market_df,
        position_held=True,
    )

    print("\nBUY BLOCKED - ALREADY HOLDING")
    print(result)

    assert result["fundamental_pass"] is True
    assert result["volume_breakout"] is True
    assert result["price_momentum"] is True

    assert result["position_held"] is True
    assert result["buy_signal"] is False


# ==========================================================
# MAIN
# ==========================================================


if __name__ == "__main__":

    # SELL
    test_holding_and_price_break_ma20()
    test_not_holding()
    test_holding_without_exit_condition()

    # BUY
    test_buy_all_conditions_pass()
    test_buy_blocked_when_price_momentum_fails()
    test_buy_blocked_when_volume_breakout_fails()
    test_buy_blocked_when_fundamental_fails()
    test_buy_blocked_when_already_holding()

    print()
    print("==========================================")
    print("ALL SIGNAL ENGINE TESTS PASSED")
    print("==========================================")