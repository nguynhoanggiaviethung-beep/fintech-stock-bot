import pandas as pd

from data.market_cache import MarketCache


def test_market_cache_set_and_get():
    cache = MarketCache()

    df = pd.DataFrame(
        {
            "symbol": ["VNINDEX", "VNINDEX"],
            "close": [1800.0, 1816.93],
            "volume": [400_000_000, 531_618_157],
        }
    )

    cache.set(df)

    result = cache.get()

    assert result is not None
    assert len(result) == 2
    assert result.iloc[-1]["close"] == 1816.93


def test_market_cache_latest():
    cache = MarketCache()

    df = pd.DataFrame(
        {
            "close": [1800.0, 1816.93],
            "volume": [400_000_000, 531_618_157],
        }
    )

    cache.set(df)

    latest = cache.get_latest()

    assert latest is not None
    assert latest["close"] == 1816.93


def test_market_cache_empty():
    cache = MarketCache()

    assert cache.is_empty()
    assert cache.get() is None
    assert cache.get_latest() is None


def test_market_cache_clear():
    cache = MarketCache()

    df = pd.DataFrame({"close": [1816.93]})
    cache.set(df)

    cache.clear()

    assert cache.is_empty()
    assert cache.get() is None
    assert cache.get_updated_at() is None