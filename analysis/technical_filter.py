from __future__ import annotations

import pandas as pd


class TechnicalFilter:
    """
    Bộ lọc kỹ thuật cho chiến lược 2.

    Điều kiện Volume theo đề bài:

        Volume hiện tại >= 1.5 * Average Volume 20 phiên

    Ngoài Volume Breakout, bộ lọc bổ sung:

        Price Momentum:
        Giá đóng cửa hiện tại > Price MA20

    Average Volume 20 được tính trên 20 phiên
    trước đó để tránh sử dụng chính Volume hiện tại.
    """

    def __init__(
        self,
        volume_window: int = 20,
        price_window: int = 20,
        breakout_ratio: float = 1.5,
    ):
        if volume_window <= 0:
            raise ValueError(
                "volume_window must be > 0"
            )

        if price_window <= 0:
            raise ValueError(
                "price_window must be > 0"
            )

        if breakout_ratio <= 0:
            raise ValueError(
                "breakout_ratio must be > 0"
            )

        self.volume_window = volume_window
        self.price_window = price_window
        self.breakout_ratio = breakout_ratio

    def calculate_volume_indicators(
        self,
        market_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Tính:

        - volume_ma20
        - volume_ratio
        - volume_breakout
        """

        if market_df.empty:
            return market_df.copy()

        required_columns = {
            "volume",
        }

        missing_columns = (
            required_columns
            - set(market_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Thiếu cột dữ liệu: "
                f"{sorted(missing_columns)}"
            )

        df = market_df.copy()

        if "timestamp" in df.columns:
            df = df.sort_values(
                "timestamp",
                ascending=True,
            ).reset_index(drop=True)

        df["volume_ma20"] = (
            df["volume"]
            .shift(1)
            .rolling(
                window=self.volume_window,
                min_periods=self.volume_window,
            )
            .mean()
        )

        df["volume_ratio"] = (
            df["volume"]
            / df["volume_ma20"]
        )

        df["volume_breakout"] = (
            df["volume_ratio"]
            >= self.breakout_ratio
        )

        return df

    def calculate_price_indicators(
        self,
        market_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Tính:

        - price_ma20
        - price_momentum

        Price Momentum:

            close > price_ma20
        """

        if market_df.empty:
            return market_df.copy()

        required_columns = {
            "close",
        }

        missing_columns = (
            required_columns
            - set(market_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Thiếu cột dữ liệu: "
                f"{sorted(missing_columns)}"
            )

        df = market_df.copy()

        if "timestamp" in df.columns:
            df = df.sort_values(
                "timestamp",
                ascending=True,
            ).reset_index(drop=True)

        df["price_ma20"] = (
            df["close"]
            .rolling(
                window=self.price_window,
                min_periods=self.price_window,
            )
            .mean()
        )

        df["price_momentum"] = (
            df["close"]
            > df["price_ma20"]
        )

        return df

    def calculate_indicators(
        self,
        market_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Tính toàn bộ chỉ tiêu kỹ thuật:

        Volume:
        - volume_ma20
        - volume_ratio
        - volume_breakout

        Price:
        - price_ma20
        - price_momentum
        """

        if market_df.empty:
            return market_df.copy()

        volume_df = self.calculate_volume_indicators(
            market_df
        )

        price_df = self.calculate_price_indicators(
            market_df
        )

        price_columns = {
            "price_ma20",
            "price_momentum",
        }

        for column in price_columns:
            volume_df[column] = price_df[column]

        return volume_df

    def check_latest(
        self,
        market_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra phiên giao dịch mới nhất.

        Returns
        -------
        dict
            Kết quả kiểm tra Volume Breakout
            và Price Momentum.
        """

        if market_df.empty:
            return {
                "symbol": None,
                "datetime": None,
                "volume": None,
                "volume_ma20": None,
                "volume_ratio": None,
                "volume_breakout": False,
                "close": None,
                "price_ma20": None,
                "price_momentum": False,
            }

        df = self.calculate_indicators(
            market_df
        )

        latest = df.iloc[-1]

        return {
            "symbol": latest.get("symbol"),
            "datetime": latest.get("datetime"),
            "volume": latest.get("volume"),
            "volume_ma20": latest.get(
                "volume_ma20"
            ),
            "volume_ratio": latest.get(
                "volume_ratio"
            ),
            "volume_breakout": bool(
                latest.get(
                    "volume_breakout",
                    False,
                )
            ),
            "close": latest.get("close"),
            "price_ma20": latest.get(
                "price_ma20"
            ),
            "price_momentum": bool(
                latest.get(
                    "price_momentum",
                    False,
                )
            ),
        }