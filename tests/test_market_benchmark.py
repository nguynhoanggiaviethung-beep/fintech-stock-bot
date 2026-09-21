from data.data_manager import MarketDataManager


def test_vnindex_data():
    manager = MarketDataManager()

    df = manager.get_historical_index(
        index_symbol="VNINDEX",
        days=180,
    )

    assert not df.empty

    required_columns = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in required_columns:
        assert column in df.columns

    print("VNINDEX DATA")
    print(df.tail())

    print()
    print("Latest close:", df.iloc[-1]["close"])
    print("Number of sessions:", len(df))

    print()
    print("ALL VNINDEX BENCHMARK DATA TESTS PASSED")


if __name__ == "__main__":
    test_vnindex_data()
