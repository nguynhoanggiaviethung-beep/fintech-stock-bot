from __future__ import annotations

import pandas as pd

from analysis.fundamental_filter import FundamentalFilter
from analysis.technical_filter import TechnicalFilter
from analysis.exit_filter import ExitFilter


class SignalEngine:
    """
    Signal Engine cho Strategy 2.

    BUY:

        1. Revenue Growth > 15%
        2. Net Income Growth > 15%
        3. ROE > 15%
        4. Volume Breakout >= 1.5x Volume MA20
        5. Price Momentum: Close > Price MA20

    SELL:

        Chỉ xét SELL khi đang HOLDING.

        SELL được kích hoạt bởi ExitFilter:

        1. Stop Loss
        2. Trailing Stop
        3. Price Break MA20
        4. Volume Reversal

    Nếu không có BUY hoặc SELL:

        NO_SIGNAL
    """

    def __init__(
        self,
        min_revenue_growth: float = 15.0,
        min_net_income_growth: float = 15.0,
        min_roe: float = 15.0,
        volume_breakout_ratio: float = 1.5,
        price_window: int = 20,
        volume_window: int = 20,
        stop_loss_pct: float = 5.0,
        trailing_stop_pct: float = 5.0,
    ):
        # ==========================================
        # FUNDAMENTAL FILTER
        # ==========================================

        self.fundamental_filter = FundamentalFilter(
            min_revenue_growth=min_revenue_growth,
            min_net_income_growth=min_net_income_growth,
            min_roe=min_roe,
        )

        # ==========================================
        # TECHNICAL FILTER
        # ==========================================

        self.technical_filter = TechnicalFilter(
            volume_window=volume_window,
            price_window=price_window,
            breakout_ratio=volume_breakout_ratio,
        )

        # ==========================================
        # EXIT FILTER
        # ==========================================

        self.exit_filter = ExitFilter(
            price_window=price_window,
            volume_window=volume_window,
            volume_breakout_ratio=volume_breakout_ratio,
            stop_loss_pct=stop_loss_pct,
            trailing_stop_pct=trailing_stop_pct,
        )

    def analyze(
        self,
        market_df: pd.DataFrame,
        fundamental_df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        position_held: bool = False,
        entry_price: float | None = None,
        highest_price: float | None = None,
    ) -> dict:
        """
        Phân tích tín hiệu BUY / SELL / NO_SIGNAL.

        BUY chỉ xét khi chưa có vị thế.

        SELL chỉ xét khi đang HOLDING.
        """

        # ==========================================
        # 1. FUNDAMENTAL ANALYSIS
        # ==========================================

        fundamental_result = (
            self.fundamental_filter.check_latest(
                fundamental_df
            )
        )

        # ==========================================
        # 2. TECHNICAL ANALYSIS
        # ==========================================

        technical_result = (
            self.technical_filter.check_latest(
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

        # ==========================================
        # 3. BUY SIGNAL
        # ==========================================

        buy_signal = bool(
            fundamental_result[
                "fundamental_pass"
            ]
            and volume_breakout
            and price_momentum
            and not position_held
        )

        # ==========================================
        # 4. SELL ANALYSIS
        # ==========================================

        sell_result = (
            self.exit_filter.check_latest(
                market_df=market_df,
                position_held=position_held,
                entry_price=entry_price,
                highest_price=highest_price,
            )
        )

        sell_signal = bool(
            sell_result.get(
                "sell_signal",
                False,
            )
        )

        # ==========================================
        # 5. FINAL SIGNAL
        # ==========================================

        if buy_signal:
            signal = "BUY"

        elif sell_signal:
            signal = "SELL"

        else:
            signal = "NO_SIGNAL"

        # ==========================================
        # 6. RETURN RESULT
        # ==========================================

        return {
            # --------------------------------------
            # GENERAL
            # --------------------------------------

            "symbol": symbol,
            "signal": signal,

            # --------------------------------------
            # BUY
            # --------------------------------------

            "buy_signal": buy_signal,

            "fundamental_pass": bool(
                fundamental_result[
                    "fundamental_pass"
                ]
            ),

            "revenue_growth": (
                fundamental_result[
                    "revenue_growth"
                ]
            ),

            "net_income_growth": (
                fundamental_result[
                    "net_income_growth"
                ]
            ),

            "roe": fundamental_result[
                "roe"
            ],

            "report_period": (
                fundamental_result[
                    "report_period"
                ]
            ),

            "volume_breakout": (
                volume_breakout
            ),

            "price_momentum": (
                price_momentum
            ),

            # --------------------------------------
            # TECHNICAL DATA
            # --------------------------------------

            "volume": technical_result.get(
                "volume"
            ),

            "volume_ma20": (
                technical_result.get(
                    "volume_ma20"
                )
            ),

            "volume_ratio": (
                technical_result.get(
                    "volume_ratio"
                )
            ),

            "close": technical_result.get(
                "close"
            ),

            "price_ma20": (
                technical_result.get(
                    "price_ma20"
                )
            ),

            # --------------------------------------
            # SELL
            # --------------------------------------

            "sell_signal": sell_signal,

            "sell_trigger": sell_result.get(
                "sell_trigger",
                False,
            ),

            "entry_price": sell_result.get(
                "entry_price"
            ),

            "highest_price": sell_result.get(
                "highest_price"
            ),

            "loss_pct": sell_result.get(
                "loss_pct"
            ),

            "stop_loss_trigger": (
                sell_result.get(
                    "stop_loss_trigger",
                    False,
                )
            ),

            "trailing_stop_price": (
                sell_result.get(
                    "trailing_stop_price"
                )
            ),

            "trailing_stop_trigger": (
                sell_result.get(
                    "trailing_stop_trigger",
                    False,
                )
            ),

            "price_break_ma20": (
                sell_result.get(
                    "price_break_ma20",
                    False,
                )
            ),

            "volume_reversal": (
                sell_result.get(
                    "volume_reversal",
                    False,
                )
            ),

            "sell_reasons": (
                sell_result.get(
                    "reasons",
                    [],
                )
            ),

            # --------------------------------------
            # POSITION STATE
            # --------------------------------------

            "position_held": (
                position_held
            ),
        }