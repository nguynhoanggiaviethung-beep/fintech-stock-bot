from __future__ import annotations

import pandas as pd


class ValuationFilter:
    """
    Bộ phân tích định giá bổ sung cho Strategy 2.

    Chỉ tiêu hiện tại:

        P/E = Giá thị trường / EPS

    P/B chưa được tính nếu dữ liệu chưa đủ
    để xác định Book Value Per Share.

    Lưu ý:
        Valuation hiện tại KHÔNG làm thay đổi
        điều kiện BUY của Strategy 2.

    Strategy 2 vẫn dựa trên:

        Quality
        + Growth
        + Volume Breakout
    """

    def __init__(self):
        pass

    @staticmethod
    def _to_number(value):
        """
        Chuyển giá trị về numeric.

        Giá trị không hợp lệ → NaN.
        """

        return pd.to_numeric(
            pd.Series([value]),
            errors="coerce",
        ).iloc[0]

    @staticmethod
    def _calculate_pe(
        price,
        eps,
    ):
        """
        Tính P/E.

        P/E = Price / EPS

        Không tính nếu:
        - Price không hợp lệ
        - EPS không hợp lệ
        - EPS <= 0
        """

        price = ValuationFilter._to_number(
            price
        )

        eps = ValuationFilter._to_number(
            eps
        )

        if pd.isna(price):
            return None

        if pd.isna(eps):
            return None

        if eps <= 0:
            return None

        return float(
            price / eps
        )

    def check_stock(
        self,
        fundamental_row: pd.Series,
        market_row: pd.Series,
    ) -> dict:
        """
        Phân tích định giá của một cổ phiếu.

        Parameters
        ----------
        fundamental_row:
            Dòng dữ liệu tài chính mới nhất.

        market_row:
            Dòng dữ liệu thị trường mới nhất.
        """

        symbol = fundamental_row.get(
            "symbol"
        )

        report_period = fundamental_row.get(
            "report_period"
        )

        eps = self._to_number(
            fundamental_row.get("eps")
        )

        price = self._to_number(
            market_row.get("close")
        )

        pe = self._calculate_pe(
            price,
            eps,
        )

        return {
            "symbol": symbol,
            "report_period": report_period,

            "price": price,
            "eps": eps,

            "pe": pe,

            # Chưa đủ dữ liệu Book Value
            # Per Share để tính P/B.
            "pb": None,

            "pe_available": bool(
                pe is not None
            ),

            "pb_available": False,
        }

    def check_latest(
        self,
        fundamental_df: pd.DataFrame,
        market_df: pd.DataFrame,
    ) -> dict:
        """
        Phân tích định giá dựa trên:

        - Fundamental record mới nhất
        - Market price mới nhất
        """

        if (
            fundamental_df is None
            or fundamental_df.empty
        ):
            return self._empty_result()

        if (
            market_df is None
            or market_df.empty
        ):
            return self._empty_result(
                symbol=fundamental_df.iloc[0].get(
                    "symbol"
                )
            )

        fundamental_row = (
            fundamental_df.iloc[0]
        )

        market_row = (
            market_df.sort_values(
                "datetime"
            ).iloc[-1]
            if "datetime" in market_df.columns
            else market_df.iloc[-1]
        )

        return self.check_stock(
            fundamental_row,
            market_row,
        )

    @staticmethod
    def _empty_result(
        symbol=None,
    ) -> dict:
        return {
            "symbol": symbol,
            "report_period": None,

            "price": None,
            "eps": None,

            "pe": None,
            "pb": None,

            "pe_available": False,
            "pb_available": False,
        }