from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from data.data_quality_filter import (
    DataQualityFilter,
)


def create_valid_market_data():
    rows = []

    start_date = datetime(2026, 1, 1)

    for i in range(25):
        rows.append(
            {
                "datetime": (
                    start_date
                    + timedelta(days=i)
                ),
                "open": 100 + i,
                "high": 105 + i,
                "low": 98 + i,
                "close": 103 + i,
                "volume": 1_000_000 + i,
            }
        )

    return pd.DataFrame(rows)


def create_valid_fundamental_data():
    return pd.DataFrame(
        [
            {
                "symbol": "ABB",
                "report_period": "2025",
                "revenue_growth": 89.47,
                "net_income_growth": 379.65,
                "roe": 18.22,
            }
        ]
    )


def test_valid_stock_data():

    market_df = (
        create_valid_market_data()
    )

    fundamental_df = (
        create_valid_fundamental_data()
    )

    validator = DataQualityFilter()

    result = validator.validate_stock_data(
        market_df=market_df,
        fundamental_df=fundamental_df,
    )

    assert result["passed"] is True

    print()
    print(
        "VALID STOCK DATA TEST"
    )
    print(
        result
    )


def test_invalid_market_data():

    market_df = (
        create_valid_market_data()
    )

    market_df.loc[0, "close"] = None

    fundamental_df = (
        create_valid_fundamental_data()
    )

    validator = DataQualityFilter()

    result = validator.validate_stock_data(
        market_df=market_df,
        fundamental_df=fundamental_df,
    )

    assert result["passed"] is False

    print()
    print(
        "INVALID MARKET DATA TEST"
    )
    print(
        result
    )


def test_invalid_fundamental_data():

    market_df = (
        create_valid_market_data()
    )

    fundamental_df = (
        create_valid_fundamental_data()
    )

    fundamental_df.loc[
        0,
        "roe",
    ] = None

    validator = DataQualityFilter()

    result = validator.validate_stock_data(
        market_df=market_df,
        fundamental_df=fundamental_df,
    )

    assert result["passed"] is False

    print()
    print(
        "INVALID FUNDAMENTAL DATA TEST"
    )
    print(
        result
    )


if __name__ == "__main__":

    test_valid_stock_data()
    test_invalid_market_data()
    test_invalid_fundamental_data()

    print()
    print(
        "ALL DATA QUALITY TESTS PASSED"
    )