from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from analysis.signal_engine import SignalEngine
from data.data_manager import DataManager


class StockDetailService:
    """
    Service phân tích chi tiết một mã cổ phiếu.

    Nhiệm vụ:

        Symbol
          ↓
        Market Data
          ↓
        Fundamental Data
          ↓
        Signal Engine
          ↓
        Stock Detail Snapshot

    Service này sẽ được sử dụng bởi:
        - Telegram /stock command
        - Chart
        - Alert
        - Signal display
    """

    def __init__(
        self,
        lookback_days: int = 90,
    ):
        self.data_manager = DataManager()
        self.signal_engine = SignalEngine()

        self.lookback_days = lookback_days

    def get_stock_detail(
        self,
        symbol: str,
    ) -> dict:
        """
        Lấy toàn bộ thông tin phân tích
        cho một mã cổ phiếu.
        """

        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError(
                "Stock symbol không được để trống."
            )

        # -------------------------------------------------
        # Time range
        # -------------------------------------------------

        end_date = datetime.now(
            timezone.utc
        )

        start_date = (
            end_date
            - timedelta(
                days=self.lookback_days
            )
        )

        start_timestamp = int(
            start_date.timestamp()
        )

        end_timestamp = int(
            end_date.timestamp()
        )

        # -------------------------------------------------
        # Market data
        # -------------------------------------------------

        market_df = (
            self.data_manager.get_market_data(
                symbol,
                start_timestamp,
                end_timestamp,
            )
        )

        if market_df.empty:
            raise ValueError(
                f"Không có market data cho {symbol}."
            )

        # -------------------------------------------------
        # Fundamental data
        # -------------------------------------------------

        fundamental_df = (
            self.data_manager.get_fundamental_data(
                symbol
            )
        )

        if fundamental_df.empty:
            raise ValueError(
                f"Không có fundamental data cho {symbol}."
            )

        # -------------------------------------------------
        # Signal
        # -------------------------------------------------

        signal_result = (
            self.signal_engine.analyze(
                fundamental_df=fundamental_df,
                market_df=market_df,
            )
        )

        # -------------------------------------------------
        # Latest market row
        # -------------------------------------------------

        latest_market = (
            market_df
            .sort_values(
                "datetime"
            )
            .iloc[-1]
        )

        # -------------------------------------------------
        # Prepare chart data
        # -------------------------------------------------

        chart_df = market_df.copy()

        chart_df = (
            chart_df
            .sort_values(
                "datetime"
            )
            .reset_index(drop=True)
        )

        # Volume indicators
        technical_df = (
            self.signal_engine
            .technical_filter
            .calculate_volume_indicators(
                chart_df
            )
        )

        # -------------------------------------------------
        # Latest price
        # -------------------------------------------------

        latest_price = latest_market.get(
            "close"
        )

        if latest_price is None:
            latest_price = latest_market.get(
                "c"
            )

        # -------------------------------------------------
        # Snapshot
        # -------------------------------------------------

        snapshot = {
            "symbol": symbol,

            "datetime": latest_market.get(
                "datetime"
            ),

            "price": latest_price,

            "open": latest_market.get(
                "open"
            ),

            "high": latest_market.get(
                "high"
            ),

            "low": latest_market.get(
                "low"
            ),

            "volume": signal_result.get(
                "volume"
            ),

            "volume_ma20": signal_result.get(
                "volume_ma20"
            ),

            "volume_ratio": signal_result.get(
                "volume_ratio"
            ),

            "revenue_growth": signal_result.get(
                "revenue_growth"
            ),

            "net_income_growth": signal_result.get(
                "net_income_growth"
            ),

            "roe": signal_result.get(
                "roe"
            ),

            "report_period": signal_result.get(
                "report_period"
            ),

            "fundamental_pass": signal_result.get(
                "fundamental_pass"
            ),

            "volume_breakout": signal_result.get(
                "volume_breakout"
            ),

            "signal": signal_result.get(
                "signal"
            ),
        }

        return {
            "symbol": symbol,

            "snapshot": snapshot,

            "market_data": chart_df,

            "technical_data": technical_df,

            "fundamental_data": fundamental_df,

            "signal": signal_result,

            "data_range": {
                "start": start_date,
                "end": end_date,
            },
        }

    @staticmethod
    def format_summary(
        detail: dict,
    ) -> str:
        """
        Chuyển stock detail thành text summary.

        Sau này Telegram có thể sử dụng trực tiếp
        method này để gửi thông tin cho người dùng.
        """

        snapshot = detail["snapshot"]

        symbol = snapshot["symbol"]
        signal = snapshot["signal"]

        price = snapshot["price"]
        volume = snapshot["volume"]
        volume_ma20 = snapshot["volume_ma20"]
        volume_ratio = snapshot["volume_ratio"]

        revenue_growth = snapshot[
            "revenue_growth"
        ]

        net_income_growth = snapshot[
            "net_income_growth"
        ]

        roe = snapshot["roe"]

        fundamental_pass = snapshot[
            "fundamental_pass"
        ]

        volume_breakout = snapshot[
            "volume_breakout"
        ]

        report_period = snapshot[
            "report_period"
        ]

        def format_number(
            value,
            decimals=2,
        ):
            if pd.isna(value):
                return "N/A"

            return f"{value:,.{decimals}f}"

        def format_percent(
            value,
        ):
            if pd.isna(value):
                return "N/A"

            return f"{value:+.2f}%"

        lines = [
            f"STOCK: {symbol}",
            "",
            f"Signal: {signal}",
            "",
            "MARKET",
            f"Price: {format_number(price)}",
            f"Volume: {format_number(volume, 0)}",
            f"Volume MA20: {format_number(volume_ma20, 0)}",
            f"Volume Ratio: "
            f"{format_number(volume_ratio)}x",
            "",
            "FUNDAMENTAL",
            f"Report Period: {report_period}",
            f"Revenue Growth: "
            f"{format_percent(revenue_growth)}",
            f"Net Income Growth: "
            f"{format_percent(net_income_growth)}",
            f"ROE: {format_percent(roe)}",
            "",
            "STRATEGY",
            f"Fundamental Filter: "
            f"{'PASS' if fundamental_pass else 'FAIL'}",
            f"Volume Breakout: "
            f"{'PASS' if volume_breakout else 'FAIL'}",
            f"Signal: {signal}",
        ]

        return "\n".join(lines)