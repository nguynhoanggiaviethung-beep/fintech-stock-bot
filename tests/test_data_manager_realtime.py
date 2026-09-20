from data.data_manager import DataManager


def main():
    manager = DataManager()

    symbol = "ABB"

    realtime = manager.get_realtime_trade(
        symbol=symbol
    )

    assert realtime["symbol"] == symbol
    assert realtime["price"] is not None
    assert realtime["volume"] is not None

    print("PASS: DataManager realtime")
    print()
    print(realtime)

    print()
    print("ALL DATA MANAGER REALTIME TESTS PASSED")


if __name__ == "__main__":
    main()