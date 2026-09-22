from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd

from analysis.signal_engine import SignalEngine
from data.data_manager import DataManager
from data.data_quality_filter import DataQualityFilter
from data.stock_universe import StockUniverse


class StockScanner:
    """
    Scanner toàn bộ stock universe để tìm tín hiệu đầu tư.

    Pipeline:

        Stock Universe
            ↓
        Market Data
            ↓
        Data Quality Filter
            ↓
        Fundamental Data
            ↓
        Fundamental Quality Check
            ↓
        Signal Engine
            ↓
        BUY / NO_SIGNAL

    Data Quality Filter chỉ kiểm tra dữ liệu
    có đủ và hợp lệ hay không.

    Nó không đánh giá cổ phiếu tốt hay xấu.
    """

    def __init__(
        self,
        page_size: int = 100,
        lookback_days: int = 90,
        request_delay: float = 0.2,
        end_date: datetime | None = None,
    ):
        self.universe = StockUniverse(
            page_size=page_size
        )

        self.data_manager = DataManager()

        self.data_quality_filter = (
            DataQualityFilter()
        )

        self.signal_engine = SignalEngine()

        self.lookback_days = lookback_days
        self.request_delay = request_delay

        if end_date is None:
            end_date = datetime.now(
                timezone.utc
            )

        self.end_date = end_date

        self.start_date = (
            self.end_date
            - timedelta(
                days=self.lookback_days
            )
        )

        self.start_timestamp = int(
            self.start_date.timestamp()
        )

        self.end_timestamp = int(
            self.end_date.timestamp()
        )

    # ==================================================
    # SCAN ONE SYMBOL
    # ==================================================

    def scan_symbol(
        self,
        symbol: str,
    ) -> dict | None:
        """
        Scan một mã cổ phiếu.

        Trình tự:

            Market Data
                ↓
            Data Quality
                ↓
            Fundamental Data
                ↓
            Fundamental Quality
                ↓
            Signal Engine
        """

        symbol = symbol.upper().strip()

        try:
            # ------------------------------------------
            # 1. MARKET DATA
            # ------------------------------------------

            market_df = (
                self.data_manager.get_market_data(
                    symbol,
                    self.start_timestamp,
                    self.end_timestamp,
                )
            )

            if market_df.empty:
                print(
                    f"[SKIP] {symbol}: "
                    "no market data"
                )
                return None

            # ------------------------------------------
            # 2. FUNDAMENTAL DATA
            # ------------------------------------------

            fundamental_df = (
                self.data_manager.get_fundamental_data(
                    symbol
                )
            )

            if fundamental_df.empty:
                print(
                    f"[SKIP] {symbol}: "
                    "no fundamental data"
                )
                return None

            # ------------------------------------------
            # 3. DATA QUALITY FILTER
            # ------------------------------------------

            quality_result = (
                self.data_quality_filter
                .validate_stock_data(
                    market_df=market_df,
                    fundamental_df=fundamental_df,
                )
            )

            if not quality_result["passed"]:

                print(
                    f"[SKIP] {symbol}: "
                    "data quality failed"
                )

                for error in (
                    quality_result["errors"]
                ):
                    print(
                        f"       - {error}"
                    )

                return None

            # ------------------------------------------
            # 4. SIGNAL ENGINE
            # ------------------------------------------

            result = (
                self.signal_engine.analyze(
                    fundamental_df=fundamental_df,
                    market_df=market_df,
                    symbol=symbol,
                )
            )

            return result

        except Exception as exc:

            print(
                f"[ERROR] {symbol}: "
                f"{type(exc).__name__}: {exc}"
            )

            return None

    # ==================================================
    # SCAN MULTIPLE SYMBOLS
    # ==================================================

    def scan_symbols(
        self,
        symbols: list[str],
    ) -> tuple[list[dict], dict]:

        results = []

        statistics = {
            "total": len(symbols),
            "total_symbols": len(symbols),

            "market_data_ok": 0,
            "market_data_empty": 0,

            "technical_candidates": 0,
            "technical_rejects": 0,

            "fundamental_data_ok": 0,
            "fundamental_data_empty": 0,

            "data_quality_pass": 0,
            "data_quality_fail": 0,

            "fundamental_pass": 0,
            "volume_breakout": 0,

            "buy_signals": 0,

            "errors": 0,
        }

        # ==================================================
        # 1. LẤY MARKET DATA SONG SONG
        # ==================================================

        def fetch_market_data(symbol: str):

            symbol = (
                symbol
                .upper()
                .strip()
            )

            try:

                market_df = (
                    self.data_manager.get_market_data(
                        symbol,
                        self.start_timestamp,
                        self.end_timestamp,
                    )
                )

                return (
                    symbol,
                    market_df,
                    None,
                )

            except Exception as exc:

                return (
                    symbol,
                    None,
                    exc,
                )

        print(
            f"Starting technical scan "
            f"for {len(symbols)} stocks..."
        )

        market_results = {}

        max_workers = 8

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            futures = {
                executor.submit(
                    fetch_market_data,
                    symbol,
                ): symbol
                for symbol in symbols
            }

            for index, future in enumerate(
                as_completed(futures),
                start=1,
            ):

                symbol = futures[future]

                try:

                    (
                        symbol,
                        market_df,
                        error,
                    ) = future.result()

                    if error is not None:

                        statistics[
                            "errors"
                        ] += 1

                        print(
                            f"[ERROR] {symbol}: "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )

                        continue

                    if (
                        market_df is None
                        or market_df.empty
                    ):

                        statistics[
                            "market_data_empty"
                        ] += 1

                        continue

                    statistics[
                        "market_data_ok"
                    ] += 1

                    market_results[
                        symbol
                    ] = market_df

                except Exception as exc:

                    statistics[
                        "errors"
                    ] += 1

                    print(
                        f"[ERROR] {symbol}: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                if (
                    index % 100 == 0
                    or index == len(symbols)
                ):

                    print(
                        f"Market scan progress: "
                        f"{index}/{len(symbols)}"
                    )

        # ==================================================
        # 2. TECHNICAL PRE-FILTER
        # ==================================================

        technical_candidates = []

        for symbol, market_df in (
            market_results.items()
        ):

            try:

                technical_result = (
                    self.signal_engine
                    .technical_filter
                    .check_latest(
                        market_df
                    )
                )

                volume_breakout = bool(
                    technical_result.get(
                        "volume_breakout",
                        False,
                    )
                )

                price_momentum = bool(
                    technical_result.get(
                        "price_momentum",
                        False,
                    )
                )

                # Strategy 2 technical gate
                if (
                    volume_breakout
                    and price_momentum
                ):

                    technical_candidates.append(
                        (
                            symbol,
                            market_df,
                        )
                    )

                    statistics[
                        "technical_candidates"
                    ] += 1

                else:

                    statistics[
                        "technical_rejects"
                    ] += 1

            except Exception as exc:

                statistics[
                    "errors"
                ] += 1

                print(
                    f"[ERROR] Technical "
                    f"{symbol}: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

        print(
            "Technical candidates: "
            f"{len(technical_candidates)}"
        )

        # ==================================================
        # 3. CHỈ LẤY FUNDAMENTAL CHO CÁC MÃ ĐẠT TECHNICAL
        # ==================================================

        for index, (
            symbol,
            market_df,
        ) in enumerate(
            technical_candidates,
            start=1,
        ):

            print(
                f"[FUNDAMENTAL "
                f"{index}/"
                f"{len(technical_candidates)}] "
                f"{symbol}"
            )

            try:

                fundamental_df = (
                    self.data_manager
                    .get_fundamental_data(
                        symbol
                    )
                )

                if fundamental_df.empty:

                    statistics[
                        "fundamental_data_empty"
                    ] += 1

                    print(
                        f"  [SKIP] {symbol}: "
                        "no fundamental data"
                    )

                    continue

                statistics[
                    "fundamental_data_ok"
                ] += 1

                # ==========================================
                # DATA QUALITY
                # ==========================================

                quality_result = (
                    self.data_quality_filter
                    .validate_stock_data(
                        market_df=market_df,
                        fundamental_df=fundamental_df,
                    )
                )

                if not quality_result[
                    "passed"
                ]:

                    statistics[
                        "data_quality_fail"
                    ] += 1

                    print(
                        f"  [SKIP] {symbol}: "
                        "data quality failed"
                    )

                    continue

                statistics[
                    "data_quality_pass"
                ] += 1

                # ==========================================
                # SIGNAL ENGINE
                # ==========================================

                result = (
                    self.signal_engine.analyze(
                        fundamental_df=fundamental_df,
                        market_df=market_df,
                        symbol=symbol,
                    )
                )

                results.append(
                    result
                )

                if result.get(
                    "fundamental_pass"
                ):

                    statistics[
                        "fundamental_pass"
                    ] += 1

                if result.get(
                    "volume_breakout"
                ):

                    statistics[
                        "volume_breakout"
                    ] += 1

                if result.get(
                    "signal"
                ) == "BUY":

                    statistics[
                        "buy_signals"
                    ] += 1

                    print(
                        f"  🟢 BUY: "
                        f"{symbol}"
                    )

                else:

                    print(
                        f"  Signal: "
                        f"{result.get('signal')}"
                    )

            except Exception as exc:

                statistics[
                    "errors"
                ] += 1

                print(
                    f"  [ERROR] {symbol}: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            if self.request_delay > 0:

                time.sleep(
                    self.request_delay
                )

        # ==================================================
        # SUMMARY
        # ==================================================

        print(
            "\n========== SCAN SUMMARY =========="
        )

        print(
            f"Universe: "
            f"{statistics['total_symbols']}"
        )

        print(
            f"Market data OK: "
            f"{statistics['market_data_ok']}"
        )

        print(
            f"Technical candidates: "
            f"{statistics['technical_candidates']}"
        )

        print(
            f"Fundamental checked: "
            f"{statistics['fundamental_data_ok']}"
        )

        print(
            f"BUY signals: "
            f"{statistics['buy_signals']}"
        )

        print(
            f"Errors: "
            f"{statistics['errors']}"
        )

        print(
            "=================================="
        )

        return (
            results,
            statistics,
        )
    # ==================================================
    # SCAN ALL
    # ==================================================

    def scan_all(
        self,
        limit: int | None = None,
    ) -> tuple[list[dict], dict]:

        symbols = (
            self.universe.get_symbols()
        )

        total_universe = len(symbols)

        if limit is not None:
            symbols = symbols[:limit]

        print(
            f"Total stock universe: "
            f"{total_universe}"
        )

        print(
            f"Stocks to scan: "
            f"{len(symbols)}"
        )

        print(
            f"Data start: "
            f"{self.start_date}"
        )

        print(
            f"Data end: "
            f"{self.end_date}"
        )

        print(
            f"Lookback days: "
            f"{self.lookback_days}"
        )

        return self.scan_symbols(
            symbols
        )

    # ==================================================
    # RESULT HELPERS
    # ==================================================

    @staticmethod
    def get_buy_signals(
        results: list[dict],
    ) -> list[dict]:

        return [
            result
            for result in results
            if result.get(
                "signal"
            ) == "BUY"
        ]

    @staticmethod
    def to_dataframe(
        results: list[dict],
    ) -> pd.DataFrame:

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(
            results
        )

    # ==================================================
    # PRINT STATISTICS
    # ==================================================

    @staticmethod
    def print_statistics(
        statistics: dict,
    ) -> None:

        print()

        print(
            "=" * 60
        )

        print(
            "SCAN STATISTICS"
        )

        print(
            "=" * 60
        )

        print(
            f"Total:                "
            f"{statistics['total']}"
        )

        print(
            f"Market data OK:       "
            f"{statistics['market_data_ok']}"
        )

        print(
            f"Market data empty:    "
            f"{statistics['market_data_empty']}"
        )

        print(
            f"Fundamental OK:       "
            f"{statistics['fundamental_data_ok']}"
        )

        print(
            f"Fundamental empty:    "
            f"{statistics['fundamental_data_empty']}"
        )

        print(
            f"Data quality PASS:    "
            f"{statistics['data_quality_pass']}"
        )

        print(
            f"Data quality FAIL:    "
            f"{statistics['data_quality_fail']}"
        )

        print(
            f"Fundamental PASS:     "
            f"{statistics['fundamental_pass']}"
        )

        print(
            f"Volume breakout:      "
            f"{statistics['volume_breakout']}"
        )

        print(
            f"BUY signals:          "
            f"{statistics['buy_signals']}"
        )

        print(
            f"Errors:               "
            f"{statistics['errors']}"
        )

        print(
            "=" * 60
        )