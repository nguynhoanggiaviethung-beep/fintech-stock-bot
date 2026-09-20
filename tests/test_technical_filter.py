from __future__ import annotations

import pandas as pd

from analysis.technical_filter import TechnicalFilter


def create_test_data() -> pd.DataFrame:
    dates = pd.date_range(
        start="2026-01-01",
        periods=25,
        freq="D",
    )

    data = []

    # 20 phiên đầu dùng để tính Volume MA20.
    for i in range(20):
        data.append(
            {
                "datetime": dates[i],
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0,
                "volume": 1000,
            }
        )

    # Phiên thứ 21:
    # Volume = 1600
    # Volume MA20 = 1000
    # Ratio = 1.6 >= 1.5
    data.append(
        {
            "datetime": dates[20],
            "open": 10.0,
            "high": 10.8,
            "low": 9.8,
            "close": 10.5,
            "volume": 1600,
        }
    )

    # Các phiên còn lại.
    for i in range(21, 25):
        data.append(
            {
                "datetime": dates[i],
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0,
                "volume": 1000,
            }
        )

    return pd.DataFrame(data)


def test_volume_ma20_uses_previous_20_sessions():
    technical_filter = TechnicalFilter(
        volume_window=20,
        breakout_ratio=1.5,
    )

    df = create_test_data()

    result = technical_filter.calculate_volume_indicators(df)

    latest = result.iloc[20]

    assert latest["volume_ma20"] == 1000
    assert latest["volume_ratio"] == 1.6
    assert bool(latest["volume_breakout"]) is True

    print("VOLUME MA20 TEST PASSED")


def test_volume_breakout_not_triggered():
    technical_filter = TechnicalFilter(
        volume_window=20,
        breakout_ratio=1.5,
    )

    df = create_test_data()

    # Thay volume phiên thứ 21 từ 1600 xuống 1400.
    # Ratio = 1.4 < 1.5.
    df.loc[20, "volume"] = 1400

    result = technical_filter.calculate_volume_indicators(df)

    latest = result.iloc[20]

    assert latest["volume_ma20"] == 1000
    assert latest["volume_ratio"] == 1.4
    assert bool(latest["volume_breakout"]) is False

    print("NO BREAKOUT TEST PASSED")


def test_check_latest():
    technical_filter = TechnicalFilter(
        volume_window=20,
        breakout_ratio=1.5,
    )

    df = create_test_data()

    # check_latest() luôn kiểm tra dòng cuối,
    # nên đưa phiên breakout thứ 21 ra cuối DataFrame.
    breakout_row = df.iloc[20].copy()

    test_df = df.iloc[:21].copy()

    result = technical_filter.check_latest(test_df)

    assert result["volume"] == 1600
    assert result["volume_ma20"] == 1000
    assert result["volume_ratio"] == 1.6
    assert bool(result["volume_breakout"]) is True

    print("CHECK LATEST TEST PASSED")


def test_empty_dataframe():
    technical_filter = TechnicalFilter(
        volume_window=20,
        breakout_ratio=1.5,
    )

    df = pd.DataFrame(
        columns=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    result = technical_filter.check_latest(df)

    assert result["volume_breakout"] is False
    assert result["volume"] is None
    assert result["volume_ma20"] is None
    assert result["volume_ratio"] is None

    print("EMPTY DATA TEST PASSED")


if __name__ == "__main__":
    test_volume_ma20_uses_previous_20_sessions()
    test_volume_breakout_not_triggered()
    test_check_latest()
    test_empty_dataframe()

    print()
    print("ALL TECHNICAL FILTER TESTS PASSED")