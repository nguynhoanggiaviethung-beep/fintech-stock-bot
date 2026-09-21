from __future__ import annotations

import pandas as pd


class BenchmarkAnalyzer:
    """
    Phân tích hiệu suất của benchmark thị trường.

    Hiện tại benchmark chính là VN-Index.

    Metrics:
    - Initial value
    - Final value
    - Total return
    - Maximum drawdown

    Benchmark giả định đầu tư toàn bộ vốn vào chỉ số
    tại giá đóng cửa đầu tiên và giữ xuyên suốt kỳ phân tích.
    """

    def __init__(self, initial_value: float = 100_000_000):
        if initial_value <= 0:
            raise ValueError(
                "initial_value phải lớn hơn 0"
            )

        self.initial_value = float(initial_value)

    def run(self, benchmark_df: pd.DataFrame) -> dict:
        """
        Tính hiệu suất benchmark.

        Parameters
        ----------
        benchmark_df : pd.DataFrame
            DataFrame phải có cột:
            - datetime
            - close

        Returns
        -------
        dict
            Gồm:
            - initial_value
            - final_value
            - return_pct
            - max_drawdown
            - start_date
            - end_date
        """

        if benchmark_df is None:
            raise ValueError(
                "benchmark_df không được là None"
            )

        if benchmark_df.empty:
            return {
                "initial_value": self.initial_value,
                "final_value": self.initial_value,
                "return_pct": 0.0,
                "max_drawdown": 0.0,
                "start_date": None,
                "end_date": None,
            }

        required_columns = [
            "datetime",
            "close",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in benchmark_df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Thiếu cột benchmark: {missing_columns}"
            )

        df = benchmark_df.copy()

        df["datetime"] = pd.to_datetime(
            df["datetime"]
        )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "datetime",
                "close",
            ]
        )

        df = df[
            df["close"] > 0
        ]

        if df.empty:
            return {
                "initial_value": self.initial_value,
                "final_value": self.initial_value,
                "return_pct": 0.0,
                "max_drawdown": 0.0,
                "start_date": None,
                "end_date": None,
            }

        df = (
            df.sort_values("datetime")
            .reset_index(drop=True)
        )

        first_close = float(
            df.iloc[0]["close"]
        )

        last_close = float(
            df.iloc[-1]["close"]
        )

        # Buy-and-hold benchmark.
        benchmark_values = (
            self.initial_value
            * df["close"]
            / first_close
        )

        running_peak = (
            benchmark_values
            .cummax()
        )

        drawdown = (
            benchmark_values
            / running_peak
            - 1
        ) * 100

        final_value = float(
            benchmark_values.iloc[-1]
        )

        return_pct = (
            final_value
            / self.initial_value
            - 1
        ) * 100

        max_drawdown = float(
            drawdown.min()
        )

        return {
            "initial_value": self.initial_value,
            "final_value": final_value,
            "return_pct": float(return_pct),
            "max_drawdown": max_drawdown,
            "start_date": df.iloc[0]["datetime"],
            "end_date": df.iloc[-1]["datetime"],
        }