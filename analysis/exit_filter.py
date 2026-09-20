from __future__ import annotations

import pandas as pd


class ExitFilter:
    """
    Exit Filter cho Strategy 2.

    SELL được xem xét khi cổ phiếu đang HOLDING.

    Các điều kiện SELL:

    1. Stop Loss
       Loss >= stop_loss_pct

    2. Trailing Stop
       Giá đóng cửa giảm từ mức giá cao nhất kể từ khi BUY
       một tỷ lệ >= trailing_stop_pct.

    3. Price Break MA20
       Close < Price MA20

    4. Volume Reversal
       Volume >= volume_breakout_ratio * Volume MA20
       AND Close < Previous Close

    Final SELL:
        Stop Loss
        OR Trailing Stop
        OR Price Break MA20
        OR Volume Reversal

    Lưu ý:
        Đây là exit rule do nhóm thiết kế bổ sung cho Strategy 2.
        Không phải toàn bộ điều kiện SELL được quy định trực tiếp
        trong đề bài Strategy 2.
    """

    def __init__(
        self,
        price_window: int = 20,
        volume_window: int = 20,
        volume_breakout_ratio: float = 1.5,
        stop_loss_pct: float = 5.0,
        trailing_stop_pct: float = 5.0,
    ):
        if price_window <= 0:
            raise ValueError("price_window must be > 0")

        if volume_window <= 0:
            raise ValueError("volume_window must be > 0")

        if volume_breakout_ratio <= 0:
            raise ValueError("volume_breakout_ratio must be > 0")

        if stop_loss_pct <= 0:
            raise ValueError("stop_loss_pct must be > 0")

        if trailing_stop_pct <= 0:
            raise ValueError("trailing_stop_pct must be > 0")

        self.price_window = price_window
        self.volume_window = volume_window
        self.volume_breakout_ratio = volume_breakout_ratio
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct

    def calculate_indicators(self, market_df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính các chỉ báo phục vụ SELL.

        Required columns:
            datetime
            close
            volume
        """

        required_columns = {"datetime", "close", "volume"}

        missing_columns = required_columns - set(market_df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        if market_df.empty:
            return pd.DataFrame(
                columns=[
                    "datetime",
                    "close",
                    "volume",
                    "price_ma20",
                    "volume_ma20",
                    "previous_close",
                    "volume_ratio",
                    "price_break_ma20",
                    "volume_reversal",
                ]
            )

        df = market_df.copy()

        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        df = df.dropna(subset=["datetime", "close", "volume"])

        df = df.sort_values("datetime").reset_index(drop=True)

        # ---------------------------------------------------------
        # Price MA20
        # ---------------------------------------------------------
        df["price_ma20"] = (
            df["close"]
            .rolling(
                window=self.price_window,
                min_periods=self.price_window,
            )
            .mean()
        )

        # ---------------------------------------------------------
        # Volume MA20
        #
        # Exclude current session để tránh current volume
        # làm thay đổi chính benchmark dùng để so sánh.
        # ---------------------------------------------------------
        df["volume_ma20"] = (
            df["volume"]
            .shift(1)
            .rolling(
                window=self.volume_window,
                min_periods=self.volume_window,
            )
            .mean()
        )

        # ---------------------------------------------------------
        # Previous Close
        # ---------------------------------------------------------
        df["previous_close"] = df["close"].shift(1)

        # ---------------------------------------------------------
        # Volume Ratio
        # ---------------------------------------------------------
        df["volume_ratio"] = (
            df["volume"] / df["volume_ma20"]
        )

        # ---------------------------------------------------------
        # Price Break MA20
        # ---------------------------------------------------------
        df["price_break_ma20"] = (
            df["close"] < df["price_ma20"]
        )

        # ---------------------------------------------------------
        # Volume Reversal
        #
        # Volume >= 1.5x MA20
        # AND
        # Close < Previous Close
        # ---------------------------------------------------------
        df["volume_reversal"] = (
            (df["volume_ratio"] >= self.volume_breakout_ratio)
            & (df["close"] < df["previous_close"])
        )

        return df

    def check_latest(
        self,
        market_df: pd.DataFrame,
        position_held: bool = True,
        entry_price: float | None = None,
        highest_price: float | None = None,
    ) -> dict:
        """
        Kiểm tra điều kiện SELL tại phiên mới nhất.

        Parameters
        ----------
        market_df:
            Historical OHLCV dataframe.

        position_held:
            Có đang nắm giữ cổ phiếu hay không.

        entry_price:
            Giá BUY execution của vị thế hiện tại.

        highest_price:
            Giá cao nhất kể từ khi BUY.

        Returns
        -------
        dict
            Kết quả SELL signal và các chỉ báo liên quan.
        """

        empty_result = {
            "sell_signal": False,
            "sell_trigger": False,

            "entry_price": entry_price,
            "highest_price": highest_price,

            "loss_pct": None,
            "stop_loss_trigger": False,

            "trailing_stop_price": None,
            "trailing_stop_pct": self.trailing_stop_pct,
            "trailing_stop_trigger": False,

            "price_break_ma20": False,

            "volume": None,
            "volume_ma20": None,
            "volume_ratio": None,
            "volume_reversal": False,

            "reasons": [],
        }

        if market_df.empty:
            return empty_result

        df = self.calculate_indicators(market_df)

        if df.empty:
            return empty_result

        latest = df.iloc[-1]

        close = latest["close"]

        price_break_ma20 = bool(
            latest["price_break_ma20"]
        ) if pd.notna(latest["price_break_ma20"]) else False

        volume_reversal = bool(
            latest["volume_reversal"]
        ) if pd.notna(latest["volume_reversal"]) else False

        # =========================================================
        # STOP LOSS
        # =========================================================

        loss_pct = None
        stop_loss_trigger = False

        if (
            position_held
            and entry_price is not None
            and pd.notna(entry_price)
            and entry_price > 0
            and pd.notna(close)
        ):
            loss_pct = (
                (close - entry_price)
                / entry_price
                * 100
            )

            stop_loss_trigger = bool(
                loss_pct <= -self.stop_loss_pct
            )

        # =========================================================
        # TRAILING STOP
        # =========================================================

        trailing_stop_price = None
        trailing_stop_trigger = False

        if (
            position_held
            and highest_price is not None
            and pd.notna(highest_price)
            and highest_price > 0
            and pd.notna(close)
        ):
            trailing_stop_price = (
                highest_price
                * (1 - self.trailing_stop_pct / 100)
            )

            trailing_stop_trigger = bool(
                close <= trailing_stop_price
            )

        # =========================================================
        # FINAL SELL TRIGGER
        # =========================================================

        sell_trigger = bool(
            stop_loss_trigger
            or trailing_stop_trigger
            or price_break_ma20
            or volume_reversal
        )

        sell_signal = bool(
            position_held
            and sell_trigger
        )

        # =========================================================
        # REASONS
        # =========================================================

        reasons = []

        if position_held:

            if stop_loss_trigger:
                reasons.append(
                    f"Stop Loss: lỗ >= {self.stop_loss_pct:.2f}%"
                )

            if trailing_stop_trigger:
                reasons.append(
                    "Trailing Stop: giá đóng cửa "
                    f"<= {trailing_stop_price:.2f}"
                )

            if price_break_ma20:
                reasons.append(
                    "Giá đóng cửa dưới MA20"
                )

            if volume_reversal:
                reasons.append(
                    "Volume >= "
                    f"{self.volume_breakout_ratio:.1f}x Volume MA20 "
                    "và giá đóng cửa giảm"
                )

        return {
            "sell_signal": sell_signal,
            "sell_trigger": sell_trigger,

            "entry_price": entry_price,
            "highest_price": highest_price,

            "loss_pct": loss_pct,
            "stop_loss_trigger": stop_loss_trigger,

            "trailing_stop_price": trailing_stop_price,
            "trailing_stop_pct": self.trailing_stop_pct,
            "trailing_stop_trigger": trailing_stop_trigger,

            "price_break_ma20": price_break_ma20,

            "volume": latest["volume"],
            "volume_ma20": latest["volume_ma20"],
            "volume_ratio": latest["volume_ratio"],
            "volume_reversal": volume_reversal,

            "reasons": reasons,
        }