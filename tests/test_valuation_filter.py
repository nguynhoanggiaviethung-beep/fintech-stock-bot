from __future__ import annotations

import pandas as pd

from analysis.valuation_filter import (
    ValuationFilter,
)


def create_fundamental_data(
    eps=5000,
):
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "revenue_growth": 89.47,
                "net_income_growth": 379.65,
                "roe": 18.22,
                "eps": eps,
            }
        ]
    )


def create_market_data(
    close=25000,
):
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "datetime": "2026-09-18",
                "open": 24000,
                "high": 25500,
                "low": 23800,
                "close": close,
                "volume": 1000000,
            }
        ]
    )


def test_pe_calculation():
    fundamental_df = create_fundamental_data(
        eps=5000
    )

    market_df = create_market_data(
        close=25000
    )

    valuation_filter = ValuationFilter()

    result = valuation_filter.check_latest(
        fundamental_df,
        market_df,
    )

    # 25,000 / 5,000 = 5
    assert result["pe"] == 5.0

    assert result["pe_available"] is True
    assert result["pb_available"] is False

    print()
    print("P/E CALCULATION")
    print(result)


def test_negative_eps():
    fundamental_df = create_fundamental_data(
        eps=-1000
    )

    market_df = create_market_data(
        close=25000
    )

    valuation_filter = ValuationFilter()

    result = valuation_filter.check_latest(
        fundamental_df,
        market_df,
    )

    assert result["pe"] is None
    assert result["pe_available"] is False

    print()
    print("NEGATIVE EPS")
    print(result)


def test_missing_eps():
    fundamental_df = create_fundamental_data(
        eps=None
    )

    market_df = create_market_data(
        close=25000
    )

    valuation_filter = ValuationFilter()

    result = valuation_filter.check_latest(
        fundamental_df,
        market_df,
    )

    assert result["pe"] is None
    assert result["pe_available"] is False

    print()
    print("MISSING EPS")
    print(result)


def test_missing_market_data():
    fundamental_df = create_fundamental_data()

    market_df = pd.DataFrame()

    valuation_filter = ValuationFilter()

    result = valuation_filter.check_latest(
        fundamental_df,
        market_df,
    )

    assert result["pe"] is None
    assert result["pb"] is None

    print()
    print("MISSING MARKET DATA")
    print(result)


def test_empty_fundamental_data():
    fundamental_df = pd.DataFrame()

    market_df = create_market_data()

    valuation_filter = ValuationFilter()

    result = valuation_filter.check_latest(
        fundamental_df,
        market_df,
    )

    assert result["pe"] is None
    assert result["pb"] is None

    print()
    print("EMPTY FUNDAMENTAL DATA")
    print(result)


if __name__ == "__main__":
    test_pe_calculation()
    test_negative_eps()
    test_missing_eps()
    test_missing_market_data()
    test_empty_fundamental_data()

    print()
    print("ALL VALUATION FILTER TESTS PASSED")