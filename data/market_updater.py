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
            Bổ sung fallback: Trả về Cache cũ nếu fetch từ DNSE thất bại/timeout.
            """
            try:
                df = self.fetch_func()

                if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                    raise ValueError("DNSE không trả về dữ liệu hợp lệ hoặc bị rỗng.")

                # Cập nhật cache nếu lấy dữ liệu mới thành công
                self.cache.set(df)

                with self._lock:
                    self._update_count += 1
                    self._last_error = None

                return df

            except Exception as error:
                # Ghi lại lỗi timeout/kết nối
                with self._lock:
                    self._last_error = error

                # BẮT BÀI TIMEOUT: Thay vì ném exception ngắt bot, dùng cache hiện tại
                cached_df = self.cache.get() if hasattr(self.cache, "get") else None
                
                if cached_df is not None and not cached_df.empty:
                    print(f"[MARKET UPDATER WARNING] DNSE phản hồi chậm/lỗi ({error}). Đang dùng dữ liệu từ Cache.")
                    return cached_df
                
                # Nếu cả cache cũng chưa có dữ liệu thì mới quăng lỗi
                raise error

    def _run(self) -> None:
        """
        Background loop.
        Thay đổi: Chờ interval_seconds trước khi chạy lần tiếp theo 
        (vì start() đã gọi update_once() lần đầu tiên rồi).
        """
        while not self._stop_event.is_set():
            # Chờ đúng khoảng thời gian interval_seconds trước lần update tiếp theo
            if self._stop_event.wait(self.interval_seconds):
                break

            try:
                self.update_once()
            except Exception as error:
                with self._lock:
                    self._last_error = error

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