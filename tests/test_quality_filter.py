from __future__ import annotations

import pandas as pd

from analysis.quality_filter import (
    QualityFilter,
)


def create_fundamental_data(
    roe,
):
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "revenue_growth": 89.47,
                "net_income_growth": 379.65,
                "roe": roe,
            }
        ]
    )


def test_roe_above_threshold():

    fundamental_df = (
        create_fundamental_data(
            18.22
        )
    )

    quality_filter = QualityFilter()

    result = (
        quality_filter.check_latest(
            fundamental_df
        )
    )

    assert result["quality_pass"] is True
    assert result["roe_pass"] is True
    assert type(
        result["quality_pass"]
    ) is bool

    print()
    print(
        "ROE ABOVE THRESHOLD"
    )
    print(result)


def test_roe_equal_threshold():

    fundamental_df = (
        create_fundamental_data(
            15.0
        )
    )

    quality_filter = QualityFilter()

    result = (
        quality_filter.check_latest(
            fundamental_df
        )
    )

    assert result["quality_pass"] is False
    assert result["roe_pass"] is False
    assert type(
        result["quality_pass"]
    ) is bool

    print()
    print(
        "ROE EQUAL THRESHOLD"
    )
    print(result)


def test_roe_below_threshold():

    fundamental_df = (
        create_fundamental_data(
            10.0
        )
    )

    quality_filter = QualityFilter()

    result = (
        quality_filter.check_latest(
            fundamental_df
        )
    )

    assert result["quality_pass"] is False
    assert result["roe_pass"] is False
    assert type(
        result["quality_pass"]
    ) is bool

    print()
    print(
        "ROE BELOW THRESHOLD"
    )
    print(result)


def test_missing_roe():

    fundamental_df = (
        create_fundamental_data(
            None
        )
    )

    quality_filter = QualityFilter()

    result = (
        quality_filter.check_latest(
            fundamental_df
        )
    )

    assert result["quality_pass"] is False
    assert result["roe_pass"] is False
    assert type(
        result["quality_pass"]
    ) is bool

    print()
    print(
        "MISSING ROE"
    )
    print(result)


def test_empty_data():

    fundamental_df = (
        pd.DataFrame()
    )

    quality_filter = QualityFilter()

    result = (
        quality_filter.check_latest(
            fundamental_df
        )
    )

    assert result["quality_pass"] is False
    assert result["roe_pass"] is False
    assert type(
        result["quality_pass"]
    ) is bool

    print()
    print(
        "EMPTY FUNDAMENTAL DATA"
    )
    print(result)


if __name__ == "__main__":

    test_roe_above_threshold()
    test_roe_equal_threshold()
    test_roe_below_threshold()
    test_missing_roe()
    test_empty_data()

    print()
    print(
        "ALL QUALITY FILTER TESTS PASSED"
    )