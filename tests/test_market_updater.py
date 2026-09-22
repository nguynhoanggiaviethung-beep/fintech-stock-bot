import time

import pandas as pd

from data.market_cache import MarketCache
from data.market_updater import MarketUpdater


def test_update_once():
    cache = MarketCache()

    def fetch_market_data():
        return pd.DataFrame(
            {
                "symbol": ["VNINDEX"],
                "close": [1816.93],
                "volume": [531_618_157],
            }
        )

    updater = MarketUpdater(
        cache=cache,
        fetch_func=fetch_market_data,
        interval_seconds=60,
    )

    df = updater.update_once()

    assert not df.empty
    assert cache.is_empty() is False
    assert cache.get_latest()["close"] == 1816.93
    assert updater.get_update_count() == 1
    assert updater.get_last_error() is None


def test_update_once_rejects_empty_dataframe():
    cache = MarketCache()

    def fetch_market_data():
        return pd.DataFrame()

    updater = MarketUpdater(
        cache=cache,
        fetch_func=fetch_market_data,
        interval_seconds=60,
    )

    try:
        updater.update_once()
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "DataFrame rỗng" in str(error)


def test_update_once_handles_error():
    cache = MarketCache()

    def fetch_market_data():
        raise RuntimeError("API error")

    updater = MarketUpdater(
        cache=cache,
        fetch_func=fetch_market_data,
        interval_seconds=60,
    )

    try:
        updater.update_once()
        assert False, "Expected RuntimeError"
    except RuntimeError as error:
        assert str(error) == "API error"

    assert cache.is_empty()
    assert updater.get_update_count() == 0


def test_background_updater():
    cache = MarketCache()

    call_count = {"value": 0}

    def fetch_market_data():
        call_count["value"] += 1

        return pd.DataFrame(
            {
                "symbol": ["VNINDEX"],
                "close": [1800 + call_count["value"]],
                "volume": [500_000_000],
            }
        )

    updater = MarketUpdater(
        cache=cache,
        fetch_func=fetch_market_data,
        interval_seconds=1,
    )

    updater.start()

    try:
        assert updater.is_running()

        # First update happens immediately.
        assert updater.get_update_count() >= 1

        first_value = cache.get_latest()["close"]

        # Wait for another background update.
        time.sleep(1.5)

        assert updater.get_update_count() >= 2

        second_value = cache.get_latest()["close"]

        assert second_value > first_value

    finally:
        updater.stop()

    assert not updater.is_running()


def test_start_is_idempotent():
    cache = MarketCache()

    def fetch_market_data():
        return pd.DataFrame(
            {
                "symbol": ["VNINDEX"],
                "close": [1816.93],
            }
        )

    updater = MarketUpdater(
        cache=cache,
        fetch_func=fetch_market_data,
        interval_seconds=60,
    )

    updater.start()

    try:
        first_thread = updater._thread

        updater.start()

        second_thread = updater._thread

        assert first_thread is second_thread

    finally:
        updater.stop()