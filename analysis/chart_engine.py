from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


class ChartEngine:
    """
    Engine tạo biểu đồ phân tích kỹ thuật.

    Chart gồm:
        1. Price chart
        2. Volume chart
        3. Volume MA20

    Dữ liệu đầu vào:
        DataFrame market data từ StockDetailService.

    Output:
        PNG file để có thể gửi qua Telegram.
    """

    def __init__(
        self,
        output_dir: str = "charts",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def prepare_market_data(
        self,
        market_df: pd.DataFrame,
    ) -> pd.DataFrame:

        if market_df.empty:
            raise ValueError(
                "Market data không được để trống."
            )

        df = market_df.copy()

        required_columns = {
            "datetime",
            "close",
            "volume",
        }

        missing_columns = (
            required_columns
            - set(df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Thiếu cột market data: "
                f"{sorted(missing_columns)}"
            )

        df["datetime"] = pd.to_datetime(
            df["datetime"]
        )

        df = (
            df
            .sort_values("datetime")
            .reset_index(drop=True)
        )

        # Volume MA20 sử dụng 20 phiên
        # trước đó, giống TechnicalFilter.
        df["volume_ma20"] = (
            df["volume"]
            .shift(1)
            .rolling(
                window=20,
                min_periods=20,
            )
            .mean()
        )

        return df

    def create_stock_chart(
        self,
        symbol: str,
        market_df: pd.DataFrame,
        signal: str | None = None,
    ) -> str:

        symbol = symbol.upper().strip()

        df = self.prepare_market_data(
            market_df
        )

        # -------------------------------------------------
        # Figure
        # -------------------------------------------------

        fig, (ax_price, ax_volume) = (
            plt.subplots(
                2,
                1,
                figsize=(12, 8),
                sharex=True,
                gridspec_kw={
                    "height_ratios": [3, 1],
                },
            )
        )

        # -------------------------------------------------
        # Price
        # -------------------------------------------------

        ax_price.plot(
            df["datetime"],
            df["close"],
            linewidth=1.8,
            label="Close",
        )

        ax_price.set_title(
            f"{symbol} - Price & Volume"
        )

        ax_price.set_ylabel(
            "Price"
        )

        ax_price.grid(
            True,
            alpha=0.25,
        )

        ax_price.legend()

        # -------------------------------------------------
        # Volume
        # -------------------------------------------------

        ax_volume.bar(
            df["datetime"],
            df["volume"],
            width=0.8,
            alpha=0.7,
            label="Volume",
        )

        ax_volume.plot(
            df["datetime"],
            df["volume_ma20"],
            linewidth=1.5,
            label="Volume MA20",
        )

        ax_volume.set_ylabel(
            "Volume"
        )

        ax_volume.set_xlabel(
            "Date"
        )

        ax_volume.grid(
            True,
            alpha=0.25,
        )

        ax_volume.legend()

        # -------------------------------------------------
        # Signal
        # -------------------------------------------------

        if signal:
            fig.suptitle(
                f"{symbol} | Signal: {signal}",
                fontsize=14,
                fontweight="bold",
            )

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        fig.autofmt_xdate()

        plt.tight_layout()

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        output_path = (
            self.output_dir
            / f"{symbol}_chart.png"
        )

        fig.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
        )

        plt.close(fig)

        return str(output_path)