from __future__ import annotations

import pandas as pd

from analysis.benchmark import BenchmarkAnalyzer
from data.data_manager import MarketDataManager
from analysis.backtest_engine import BacktestEngine
from analysis.signal_engine import SignalEngine
from analysis.trade_explanation import TradeExplanation


class BacktestRunner:
    """
    Backtest Runner cho Strategy 2.

    Luồng:

    1. Fundamental data được giữ cố định trong phiên bản V1.
    2. OHLCV được đánh giá từng ngày.
    3. SignalEngine tạo tín hiệu BUY / SELL / NO_SIGNAL.
    4. TradeExplanation giải thích tín hiệu.
    5. Tín hiệu tại cuối ngày T được thực hiện
       tại OPEN của ngày T+1.
    6. Khi BUY được thực hiện tại OPEN T+1:
       - position_held = True
       - entry_price = current_open
       - highest_price = entry_price
    7. Khi đang HOLDING:
       - highest_price được cập nhật theo giá CLOSE
         cao nhất kể từ thời điểm BUY.
    8. highest_price được truyền vào ExitFilter
       thông qua SignalEngine.
    9. Khi SELL được thực hiện tại OPEN T+1:
       - position_held = False
       - entry_price = None
       - highest_price = None
    10. Trạng thái vị thế được cập nhật theo thời điểm
        thực tế của execution.

    Lưu ý:
        Fundamental data hiện vẫn là dữ liệu cố định từ input.
        Đây là giới hạn của Backtest V1 vì chưa có point-in-time
        financial statements cho từng ngày trong quá khứ.
    """

    def __init__(
        self,
        signal_engine: SignalEngine | None = None,
        backtest_engine: BacktestEngine | None = None,
        trade_explanation: TradeExplanation | None = None,
        benchmark_analyzer: BenchmarkAnalyzer | None = None,
        market_data_manager: MarketDataManager | None = None,
    ):
        self.signal_engine = (
            signal_engine
            if signal_engine is not None
            else SignalEngine()
        )

        self.backtest_engine = (
            backtest_engine
            if backtest_engine is not None
            else BacktestEngine()
        )

        self.trade_explanation = (
            trade_explanation
            if trade_explanation is not None
            else TradeExplanation()
        )

        self.benchmark_analyzer = (
            benchmark_analyzer
            if benchmark_analyzer is not None
            else BenchmarkAnalyzer()
        )

        self.market_data_manager = (
            market_data_manager
            if market_data_manager is not None
            else MarketDataManager()
        )

    def generate_signals(
        self,
        market_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
        symbol: str = "UNKNOWN",
    ) -> pd.DataFrame:
        """
        Generate daily signals and manage position state.

        BUY/SELL signal generated at close T
        is executed at open T+1.
        """

        required_columns = {
            "datetime",
            "open",
            "close",
            "volume",
        }

        missing_columns = (
            required_columns - set(market_df.columns)
        )

        if missing_columns:
            raise ValueError(
                f"Missing market columns: "
                f"{sorted(missing_columns)}"
            )

        if market_df.empty:
            return pd.DataFrame()

        df = market_df.copy()

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce",
        )

        df["open"] = pd.to_numeric(
            df["open"],
            errors="coerce",
        )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce",
        )

        df = (
            df.dropna(
                subset=[
                    "datetime",
                    "open",
                    "close",
                    "volume",
                ]
            )
            .sort_values("datetime")
            .reset_index(drop=True)
        )

        # =========================================================
        # POSITION STATE
        # =========================================================

        position_held = False
        entry_price = None

        # Highest close observed since BUY execution.
        highest_price = None

        # Pending signal generated at close T
        # to be executed at open T+1.
        pending_action = None

        results = []

        # =========================================================
        # DAILY LOOP
        # =========================================================

        for index, row in df.iterrows():

            current_datetime = row["datetime"]
            current_open = float(row["open"])
            current_close = float(row["close"])

            executed_action = None

            # =====================================================
            # 1. EXECUTE PENDING BUY / SELL AT CURRENT OPEN
            # =====================================================

            if (
                pending_action == "BUY"
                and not position_held
            ):
                position_held = True
                executed_action = "BUY"

                entry_price = current_open

                # Trailing Stop starts from the actual
                # execution price.
                highest_price = entry_price

                pending_action = None

            elif (
                pending_action == "SELL"
                and position_held
            ):
                position_held = False
                executed_action = "SELL"

                entry_price = None
                highest_price = None

                pending_action = None

            # =====================================================
            # 2. UPDATE HIGHEST PRICE WHILE HOLDING
            # =====================================================

            if position_held:

                if highest_price is None:
                    highest_price = current_close

                else:
                    highest_price = max(
                        highest_price,
                        current_close,
                    )

            # =====================================================
            # 3. USE DATA ONLY UP TO CURRENT DAY
            # =====================================================

            market_until_today = (
                df.iloc[: index + 1]
                .copy()
            )

            # =====================================================
            # 4. GENERATE SIGNAL
            # =====================================================

            result = self.signal_engine.analyze(
                market_df=market_until_today,
                fundamental_df=fundamental_df,
                symbol=symbol,
                position_held=position_held,
                entry_price=entry_price,
                highest_price=highest_price,
            )

            # =====================================================
            # 5. STORE STATE
            # =====================================================

            result["datetime"] = current_datetime
            result["open"] = current_open
            result["close"] = current_close

            result["executed_action"] = (
                executed_action
            )

            result["position_after_execution"] = (
                position_held
            )

            result["entry_price"] = entry_price
            result["highest_price"] = highest_price

            # =====================================================
            # 6. CREATE TRADE EXPLANATION
            # =====================================================

            explanation = (
                self.trade_explanation.explain(
                    result
                )
            )

            result["explanation"] = explanation

            result["explanation_summary"] = (
                explanation.get(
                    "summary",
                    "",
                )
            )

            result["explanation_reasons"] = (
                explanation.get(
                    "reasons",
                    [],
                )
            )

            result["explanation_metrics"] = (
                explanation.get(
                    "metrics",
                    {},
                )
            )

            result["explanation_text"] = (
                self.trade_explanation.to_text(
                    result
                )
            )

            # =====================================================
            # 7. CREATE NEXT-DAY PENDING ACTION
            # =====================================================

            signal = result.get("signal")

            if (
                signal == "BUY"
                and not position_held
                and pending_action is None
            ):
                pending_action = "BUY"

            elif (
                signal == "SELL"
                and position_held
                and pending_action is None
            ):
                pending_action = "SELL"

            result["pending_action"] = (
                pending_action
            )

            results.append(result)

        return pd.DataFrame(results)
    def run(
        self,
        market_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
        symbol: str = "UNKNOWN",
    ) -> dict:
        """
        Chạy backtest Strategy 2 và so sánh với VN-Index.
        """

        # =========================================================
        # 1. GENERATE STRATEGY SIGNALS
        # =========================================================

        signals_df = self.generate_signals(
            market_df=market_df,
            fundamental_df=fundamental_df,
            symbol=symbol,
        )

        # =========================================================
        # 2. RUN STRATEGY BACKTEST
        # =========================================================

        if signals_df.empty:
            backtest_input = pd.DataFrame(
                columns=[
                    "datetime",
                    "open",
                    "close",
                    "signal",
                ]
            )
        else:
            backtest_input = signals_df[
                [
                    "datetime",
                    "open",
                    "close",
                    "signal",
                ]
            ].copy()

        backtest_result = self.backtest_engine.run(
            backtest_input
        )

        # =========================================================
        # 3. PREPARE VN-INDEX BENCHMARK PERIOD
        # =========================================================

        market_datetime = pd.to_datetime(
            market_df["datetime"],
            utc=True,
        )

        start_datetime = market_datetime.min()
        end_datetime = market_datetime.max()

        if pd.isna(start_datetime) or pd.isna(end_datetime):
            benchmark_result = (
                self.benchmark_analyzer.run(
                    pd.DataFrame(
                        columns=[
                            "datetime",
                            "close",
                        ]
                    )
                )
            )

            benchmark_result["strategy_return_pct"] = float(
                backtest_result.get(
                    "total_return_pct",
                    0.0,
                )
            )

            benchmark_result["excess_return_pct"] = (
                benchmark_result["strategy_return_pct"]
                - benchmark_result["return_pct"]
            )

            return {
                "signals": signals_df,
                "backtest": backtest_result,
                "benchmark": benchmark_result,
            }

        days = max(
            1,
            int(
                (
                    end_datetime
                    - start_datetime
                ).total_seconds()
                / 86400
            )
            + 1,
        )

        # =========================================================
        # 4. GET VN-INDEX DATA
        # =========================================================

        benchmark_df = (
            self.market_data_manager
            .get_historical_index(
                index_symbol="VNINDEX",
                days=days,
            )
        )

        # Quan trọng:
        # ép datetime của VN-Index về UTC giống market_df.
        benchmark_df["datetime"] = pd.to_datetime(
            benchmark_df["datetime"],
            utc=True,
        )

        # =========================================================
        # 5. FILTER VN-INDEX TO SAME PERIOD
        # =========================================================

        benchmark_df = benchmark_df[
            (
                benchmark_df["datetime"]
                >= start_datetime
            )
            & (
                benchmark_df["datetime"]
                <= end_datetime
            )
        ].copy()

        # =========================================================
        # 6. CALCULATE BENCHMARK PERFORMANCE
        # =========================================================

        benchmark_result = (
            self.benchmark_analyzer.run(
                benchmark_df
            )
        )

        # =========================================================
        # 7. COMPARE STRATEGY VS VN-INDEX
        # =========================================================

        strategy_return = float(
            backtest_result.get(
                "total_return_pct",
                0.0,
            )
        )

        benchmark_return = float(
            benchmark_result.get(
                "return_pct",
                0.0,
            )
        )

        excess_return = (
            strategy_return
            - benchmark_return
        )

        benchmark_result["strategy_return_pct"] = (
            strategy_return
        )

        benchmark_result["excess_return_pct"] = (
            excess_return
        )

        # =========================================================
        # 8. FINAL RESULT
        # =========================================================

        return {
            "signals": signals_df,
            "backtest": backtest_result,
            "benchmark": benchmark_result,
        }