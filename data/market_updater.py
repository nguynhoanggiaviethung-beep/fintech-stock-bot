from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import pandas as pd

from data.market_cache import MarketCache


class MarketUpdater:
    """
    Background updater for market data.

    The updater periodically calls fetch_func(), stores the
    returned DataFrame in MarketCache, and keeps running even
    when one update fails.
    """

    def __init__(
        self,
        cache: MarketCache,
        fetch_func: Callable[[], pd.DataFrame],
        interval_seconds: int = 300,
    ):
        if cache is None:
            raise ValueError("cache không được là None")

        if not callable(fetch_func):
            raise TypeError("fetch_func phải là callable")

        if interval_seconds <= 0:
            raise ValueError("interval_seconds phải lớn hơn 0")

        self.cache = cache
        self.fetch_func = fetch_func
        self.interval_seconds = interval_seconds

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._last_error: Optional[Exception] = None
        self._update_count = 0
        self._lock = threading.Lock()

    def update_once(self) -> pd.DataFrame:
        """
        Fetch market data once and update the cache.

        Returns:
            The fetched DataFrame.

        Raises:
            Exception:
                Re-raises any error from fetch_func().
        """
        df = self.fetch_func()

        if df is None:
            raise ValueError("fetch_func() trả về None")

        if not isinstance(df, pd.DataFrame):
            raise TypeError("fetch_func() phải trả về pandas DataFrame")

        if df.empty:
            raise ValueError("fetch_func() trả về DataFrame rỗng")

        self.cache.set(df)

        with self._lock:
            self._update_count += 1
            self._last_error = None

        return df

    def _run(self) -> None:
        """
        Background loop.

        The first update happens immediately.
        Subsequent updates happen after interval_seconds.
        """
        while not self._stop_event.is_set():
            try:
                self.update_once()
            except Exception as error:
                with self._lock:
                    self._last_error = error

            self._stop_event.wait(self.interval_seconds)

    def start(self, update_immediately: bool = True) -> None:
        """
        Start the background updater.

        If already running, this method does nothing.
        """
        if self.is_running():
            return

        self._stop_event.clear()

        if update_immediately:
            try:
                self.update_once()
            except Exception as error:
                with self._lock:
                    self._last_error = error

        self._thread = threading.Thread(
            target=self._run,
            name="market-updater",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """
        Stop the background updater.
        """
        self._stop_event.set()

        thread = self._thread

        if thread is not None and thread.is_alive():
            thread.join(timeout=2)

        self._thread = None

    def is_running(self) -> bool:
        """
        Return True if the background thread is running.
        """
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def get_last_error(self) -> Optional[Exception]:
        """
        Return the most recent update error, if any.
        """
        with self._lock:
            return self._last_error

    def get_update_count(self) -> int:
        """
        Return the number of successful cache updates.
        """
        with self._lock:
            return self._update_count