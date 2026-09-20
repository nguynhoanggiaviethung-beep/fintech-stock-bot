from __future__ import annotations

import pandas as pd

from analysis.growth_filter import (
    GrowthFilter,
)


def create_fundamental_data(
    revenue_growth,
    net_income_growth,
):
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "revenue_growth": revenue_growth,
                "net_income_growth": net_income_growth,
                "roe": 18.22,
            }
        ]
    )


def test_both_growth_above_threshold():
    fundamental_df = create_fundamental_data(
        89.47,
        379.65,
    )

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is True
    assert result["revenue_growth_pass"] is True
    assert result["net_income_growth_pass"] is True

    assert type(result["growth_pass"]) is bool

    print()
    print("BOTH GROWTH ABOVE THRESHOLD")
    print(result)


def test_revenue_growth_below_threshold():
    fundamental_df = create_fundamental_data(
        10.0,
        379.65,
    )

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is False
    assert result["revenue_growth_pass"] is False
    assert result["net_income_growth_pass"] is True

    print()
    print("REVENUE GROWTH BELOW THRESHOLD")
    print(result)


def test_net_income_growth_below_threshold():
    fundamental_df = create_fundamental_data(
        89.47,
        10.0,
    )

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is False
    assert result["revenue_growth_pass"] is True
    assert result["net_income_growth_pass"] is False

    print()
    print("NET INCOME GROWTH BELOW THRESHOLD")
    print(result)


def test_growth_equal_threshold():
    fundamental_df = create_fundamental_data(
        15.0,
        15.0,
    )

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is False
    assert result["revenue_growth_pass"] is False
    assert result["net_income_growth_pass"] is False

    print()
    print("GROWTH EQUAL THRESHOLD")
    print(result)


def test_missing_growth():
    fundamental_df = create_fundamental_data(
        None,
        None,
    )

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is False
    assert result["revenue_growth_pass"] is False
    assert result["net_income_growth_pass"] is False

    print()
    print("MISSING GROWTH")
    print(result)


def test_empty_data():
    fundamental_df = pd.DataFrame()

    growth_filter = GrowthFilter()

    result = growth_filter.check_latest(
        fundamental_df
    )

    assert result["growth_pass"] is False
    assert result["revenue_growth_pass"] is False
    assert result["net_income_growth_pass"] is False

    print()
    print("EMPTY FUNDAMENTAL DATA")
    print(result)


if __name__ == "__main__":
    test_both_growth_above_threshold()
    test_revenue_growth_below_threshold()
    test_net_income_growth_below_threshold()
    test_growth_equal_threshold()
    test_missing_growth()
    test_empty_data()

    print()
    print("ALL GROWTH FILTER TESTS PASSED")