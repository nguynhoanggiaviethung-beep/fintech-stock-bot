from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.technical_filter import TechnicalFilter


def create_price_data() -> pd.DataFrame:
    dates = pd.date_range(
        start="2026-01-01",
        periods=21,
        freq="D",
    )

    return pd.DataFrame(
        {
            "datetime": dates,
            "close": [10.0] * 20 + [11.0],
            "volume": [1000.0] * 21,
        }
    )


def test_price_momentum_above_ma20():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    df = create_price_data()

    result = technical_filter.calculate_price_indicators(
        df
    )

    latest = result.iloc[-1]

    # MA20 bao gồm phiên hiện tại:
    #
    # 19 phiên x 10 + 1 phiên x 11
    # ----------------------------- = 10.05
    #              20
    #
    # Close = 11 > MA20 = 10.05
    # => Price Momentum = True

    assert np.isclose(
        latest["price_ma20"],
        10.05,
    )

    assert np.isclose(
        latest["close"],
        11.0,
    )

    assert bool(
        latest["price_momentum"]
    ) is True

    print(
        "PRICE MOMENTUM ABOVE MA20 TEST PASSED"
    )


def test_price_momentum_below_ma20():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    df = create_price_data()

    # Phiên cuối = 9
    df.loc[20, "close"] = 9.0

    result = technical_filter.calculate_price_indicators(
        df
    )

    latest = result.iloc[-1]

    # 19 phiên x 10 + 1 phiên x 9
    # ---------------------------- = 9.95
    #              20

    assert np.isclose(
        latest["price_ma20"],
        9.95,
    )

    assert np.isclose(
        latest["close"],
        9.0,
    )

    assert bool(
        latest["price_momentum"]
    ) is False

    print(
        "PRICE MOMENTUM BELOW MA20 TEST PASSED"
    )


def test_price_momentum_equal_ma20():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    df = create_price_data()

    # Tất cả 20 phiên cuối đều có Close = 10
    # => MA20 = 10
    # => Close = MA20
    # => Momentum = False

    df.loc[20, "close"] = 10.0

    result = technical_filter.calculate_price_indicators(
        df
    )

    latest = result.iloc[-1]

    assert np.isclose(
        latest["price_ma20"],
        10.0,
    )

    assert np.isclose(
        latest["close"],
        10.0,
    )

    assert bool(
        latest["price_momentum"]
    ) is False

    print(
        "PRICE MOMENTUM EQUAL MA20 TEST PASSED"
    )


def test_price_momentum_check_latest():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    df = create_price_data()

    result = technical_filter.check_latest(
        df
    )

    assert np.isclose(
        result["close"],
        11.0,
    )

    assert np.isclose(
        result["price_ma20"],
        10.05,
    )

    assert bool(
        result["price_momentum"]
    ) is True

    print(
        "PRICE MOMENTUM CHECK LATEST TEST PASSED"
    )


def test_price_momentum_insufficient_data():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    df = pd.DataFrame(
        {
            "datetime": pd.date_range(
                start="2026-01-01",
                periods=10,
                freq="D",
            ),
            "close": [10.0] * 10,
            "volume": [1000.0] * 10,
        }
    )

    result = technical_filter.calculate_price_indicators(
        df
    )

    latest = result.iloc[-1]

    assert pd.isna(
        latest["price_ma20"]
    )

    assert bool(
        latest["price_momentum"]
    ) is False

    print(
        "PRICE MOMENTUM INSUFFICIENT DATA TEST PASSED"
    )


def test_price_momentum_multiple_prices():
    technical_filter = TechnicalFilter(
        price_window=20,
    )

    dates = pd.date_range(
        start="2026-01-01",
        periods=25,
        freq="D",
    )

    prices = [
        10.0,
        10.1,
        10.2,
        10.3,
        10.4,
        10.5,
        10.6,
        10.7,
        10.8,
        10.9,
        11.0,
        11.1,
        11.2,
        11.3,
        11.4,
        11.5,
        11.6,
        11.7,
        11.8,
        11.9,
        12.0,
        12.1,
        12.2,
        12.3,
        12.4,
    ]

    df = pd.DataFrame(
        {
            "datetime": dates,
            "close": prices,
            "volume": [1000.0] * 25,
        }
    )

    result = technical_filter.calculate_price_indicators(
        df
    )

    latest = result.iloc[-1]

    assert pd.notna(
        latest["price_ma20"]
    )

    assert latest["close"] > latest["price_ma20"]

    assert bool(
        latest["price_momentum"]
    ) is True

    print(
        "PRICE MOMENTUM MULTIPLE PRICES TEST PASSED"
    )


if __name__ == "__main__":
    test_price_momentum_above_ma20()
    test_price_momentum_below_ma20()
    test_price_momentum_equal_ma20()
    test_price_momentum_check_latest()
    test_price_momentum_insufficient_data()
    test_price_momentum_multiple_prices()

    print()
    print(
        "=========================================="
    )
    print(
        "ALL PRICE MOMENTUM TESTS PASSED"
    )
    print(
        "=========================================="
    )