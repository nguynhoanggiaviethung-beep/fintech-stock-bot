from data.realtime_client import VnstockRealtimeClient


def main():
    client = VnstockRealtimeClient()

    symbol = "ABB"

    # ============================================================
    # TEST 1: INTRADAY
    # ============================================================

    df = client.get_intraday(
        symbol=symbol,
        page_size=1,
    )

    assert df is not None
    assert not df.empty

    required_columns = {
        "time",
        "price",
        "volume",
        "match_type",
        "id",
    }

    assert required_columns.issubset(
        set(df.columns)
    )

    print("PASS: intraday data")
    print()
    print(df)

    # ============================================================
    # TEST 2: LATEST TRADE
    # ============================================================

    latest = client.get_latest_trade(
        symbol=symbol
    )

    assert latest["symbol"] == symbol
    assert latest["price"] is not None
    assert latest["volume"] is not None

    print()
    print("PASS: latest trade")
    print()
    print(latest)

    print()
    print("ALL REAL-TIME TESTS PASSED")


if __name__ == "__main__":
    main()