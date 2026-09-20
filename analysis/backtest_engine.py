from __future__ import annotations

import pandas as pd


class BacktestEngine:
    """
    Backtest Engine cho Strategy 2.

    Quy tắc khớp lệnh:
    - Tín hiệu BUY/SELL được xác định tại cuối ngày T.
    - Lệnh được thực hiện tại giá OPEN của ngày T+1.
    - Chỉ BUY khi chưa có vị thế.
    - Chỉ SELL khi đang có vị thế.
    - Không mua/bán nhiều lần trong cùng một vị thế.

    Performance metrics:
    - Win Rate
    - Average Trade Return
    - Best Trade
    - Worst Trade
    - Gross Profit
    - Gross Loss
    - Profit Factor
    - Maximum Drawdown
    """

    def __init__(
        self,
        initial_capital: float = 100_000_000,
    ):
        self.initial_capital = float(
            initial_capital
        )

    def run(
        self,
        signals_df: pd.DataFrame,
    ) -> dict:

        if signals_df is None or signals_df.empty:
            return self._empty_result()

        required_columns = {
            "datetime",
            "open",
            "close",
            "signal",
        }

        missing_columns = (
            required_columns
            - set(signals_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Thiếu cột dữ liệu: "
                f"{sorted(missing_columns)}"
            )

        df = signals_df.copy()

        df = (
            df
            .sort_values(
                "datetime",
                ascending=True,
            )
            .reset_index(drop=True)
        )

        capital = self.initial_capital

        position_held = False
        entry_price = None
        entry_datetime = None

        pending_action = None

        trades = []

        for _, row in df.iterrows():

            current_datetime = row[
                "datetime"
            ]

            current_open = float(
                row["open"]
            )

            # ==================================
            # 1. THỰC HIỆN LỆNH ĐANG CHỜ
            # ==================================

            if (
                pending_action == "BUY"
                and not position_held
            ):

                position_held = True

                entry_price = current_open

                entry_datetime = (
                    current_datetime
                )

                pending_action = None

            elif (
                pending_action == "SELL"
                and position_held
            ):

                exit_price = current_open

                exit_datetime = (
                    current_datetime
                )

                return_pct = (
                    exit_price
                    / entry_price
                    - 1
                ) * 100

                profit_loss = (
                    capital
                    * return_pct
                    / 100
                )

                capital += profit_loss

                trades.append(
                    {
                        "entry_datetime": (
                            entry_datetime
                        ),
                        "entry_price": (
                            entry_price
                        ),
                        "exit_datetime": (
                            exit_datetime
                        ),
                        "exit_price": (
                            exit_price
                        ),
                        "return_pct": (
                            return_pct
                        ),
                        "profit_loss": (
                            profit_loss
                        ),
                    }
                )

                position_held = False

                entry_price = None

                entry_datetime = None

                pending_action = None

            # ==================================
            # 2. ĐỌC TÍN HIỆU CUỐI NGÀY
            # ==================================

            signal = row["signal"]

            if signal == "BUY":

                if (
                    not position_held
                    and pending_action is None
                ):
                    pending_action = "BUY"

            elif signal == "SELL":

                if (
                    position_held
                    and pending_action is None
                ):
                    pending_action = "SELL"

        # ======================================
        # 3. TỔNG HỢP TRADE
        # ======================================

        trades_df = pd.DataFrame(
            trades
        )

        total_trades = len(
            trades
        )

        if not trades_df.empty:

            winning_trades = int(
                (
                    trades_df["return_pct"]
                    > 0
                ).sum()
            )

            losing_trades = int(
                (
                    trades_df["return_pct"]
                    <= 0
                ).sum()
            )

        else:

            winning_trades = 0

            losing_trades = 0

        # ======================================
        # 4. PERFORMANCE METRICS
        # ======================================

        if total_trades > 0:

            win_rate = (
                winning_trades
                / total_trades
                * 100
            )

            average_trade_return = (
                trades_df["return_pct"]
                .mean()
            )

            best_trade = (
                trades_df["return_pct"]
                .max()
            )

            worst_trade = (
                trades_df["return_pct"]
                .min()
            )

            gross_profit = (
                trades_df.loc[
                    trades_df["profit_loss"]
                    > 0,
                    "profit_loss",
                ].sum()
            )

            gross_loss = (
                trades_df.loc[
                    trades_df["profit_loss"]
                    < 0,
                    "profit_loss",
                ].sum()
            )

            if gross_loss != 0:

                profit_factor = (
                    gross_profit
                    / abs(gross_loss)
                )

            else:

                profit_factor = None

            # ----------------------------------
            # Maximum Drawdown
            # ----------------------------------

            equity_curve = [
                self.initial_capital
            ]

            current_equity = (
                self.initial_capital
            )

            for profit_loss in (
                trades_df["profit_loss"]
            ):

                current_equity += (
                    profit_loss
                )

                equity_curve.append(
                    current_equity
                )

            equity_series = pd.Series(
                equity_curve
            )

            running_peak = (
                equity_series
                .cummax()
            )

            drawdown = (
                equity_series
                - running_peak
            ) / running_peak * 100

            max_drawdown = (
                drawdown.min()
            )

        else:

            win_rate = 0.0

            average_trade_return = 0.0

            best_trade = 0.0

            worst_trade = 0.0

            gross_profit = 0.0

            gross_loss = 0.0

            profit_factor = None

            max_drawdown = 0.0

        # ======================================
        # 5. TOTAL RETURN
        # ======================================

        total_return_pct = (
            capital
            / self.initial_capital
            - 1
        ) * 100

        return {
            "initial_capital": (
                self.initial_capital
            ),

            "final_capital": capital,

            "total_return_pct": (
                total_return_pct
            ),

            "total_trades": (
                total_trades
            ),

            "winning_trades": (
                winning_trades
            ),

            "losing_trades": (
                losing_trades
            ),

            "win_rate": (
                win_rate
            ),

            "average_trade_return": (
                average_trade_return
            ),

            "best_trade": (
                best_trade
            ),

            "worst_trade": (
                worst_trade
            ),

            "gross_profit": (
                gross_profit
            ),

            "gross_loss": (
                gross_loss
            ),

            "profit_factor": (
                profit_factor
            ),

            "max_drawdown": (
                max_drawdown
            ),

            "open_position": (
                position_held
            ),

            "entry_price": (
                entry_price
            ),

            "pending_action": (
                pending_action
            ),

            "trades": (
                trades_df
            ),
        }

    @staticmethod
    def _empty_result():

        return {
            "initial_capital": 0.0,

            "final_capital": 0.0,

            "total_return_pct": 0.0,

            "total_trades": 0,

            "winning_trades": 0,

            "losing_trades": 0,

            "win_rate": 0.0,

            "average_trade_return": 0.0,

            "best_trade": 0.0,

            "worst_trade": 0.0,

            "gross_profit": 0.0,

            "gross_loss": 0.0,

            "profit_factor": None,

            "max_drawdown": 0.0,

            "open_position": False,

            "entry_price": None,

            "pending_action": None,

            "trades": pd.DataFrame(),
        }