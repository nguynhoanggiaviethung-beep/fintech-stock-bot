from datetime import datetime, timezone

from data.data_manager import DataManager


def main():
    manager = DataManager()

    symbol = "ABB"

    # Lấy khoảng thời gian đủ để có dữ liệu thị trường
    now = datetime.now(timezone.utc)

    end_timestamp = int(
        now.timestamp()
    )

    start_timestamp = int(
        (
            now.timestamp() - 30 * 24 * 60 * 60
        )
    )

    snapshot = manager.get_stock_snapshot(
        symbol=symbol,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        resolution="1D",
    )

    # ============================================================
    # TEST 1: STRUCTURE
    # ============================================================

    assert snapshot["symbol"] == symbol

    assert "market" in snapshot
    assert "realtime" in snapshot
    assert "fundamental" in snapshot

    print("PASS: snapshot structure")

    # ============================================================
    # TEST 2: REALTIME
    # ============================================================

    realtime = snapshot["realtime"]

    assert realtime["symbol"] == symbol
    assert realtime["price"] is not None
    assert realtime["volume"] is not None

    print("PASS: snapshot realtime")

    # ============================================================
    # TEST 3: DISPLAY
    # ============================================================

    print()
    print("STOCK SNAPSHOT")
    print("------------------------------")
    print("Symbol:", snapshot["symbol"])

    print()
    print("Realtime:")
    print(realtime)

    print()
    print("Market:")
    print(snapshot["market"])

    print()
    print("Fundamental:")
    print(snapshot["fundamental"])

    print()
    print("ALL STOCK SNAPSHOT TESTS PASSED")


if __name__ == "__main__":
    main()