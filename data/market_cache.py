from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

import pandas as pd


class MarketCache:
    """
    In-memory cache for the latest market data.

    The cache is intentionally kept independent from Telegram
    and data-source clients so it can be tested separately.
    """

    def __init__(self):
        self._data: Optional[pd.DataFrame] = None
        self._updated_at: Optional[datetime] = None
        self._lock = threading.Lock()

    def set(self, df: pd.DataFrame) -> None:
        if df is None:
            raise ValueError("Market data không được là None")

        if not isinstance(df, pd.DataFrame):
            raise TypeError("Market data phải là pandas DataFrame")

        with self._lock:
            self._data = df.copy()
            self._updated_at = datetime.now()

    def get(self) -> Optional[pd.DataFrame]:
        with self._lock:
            if self._data is None:
                return None

            return self._data.copy()

    def get_latest(self) -> Optional[pd.Series]:
        df = self.get()

        if df is None or df.empty:
            return None

        return df.iloc[-1]

    def get_updated_at(self) -> Optional[datetime]:
        with self._lock:
            return self._updated_at

    def is_empty(self) -> bool:
        with self._lock:
            return self._data is None or self._data.empty

    def clear(self) -> None:
        with self._lock:
            self._data = None
            self._updated_at = None