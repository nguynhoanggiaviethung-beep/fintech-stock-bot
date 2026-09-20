from __future__ import annotations

import pandas as pd


class GrowthFilter:
    """
    Bộ lọc Growth của chiến lược đầu tư.

    Tiêu chí:
        Revenue Growth > 15%
        Net Income Growth > 15%

    Growth Filter chỉ đánh giá tốc độ tăng trưởng
    của doanh nghiệp.

    Không kiểm tra:
        - ROE
        - Volume
        - Valuation
    """

    def __init__(
        self,
        min_revenue_growth: float = 15.0,
        min_net_income_growth: float = 15.0,
    ):
        self.min_revenue_growth = float(
            min_revenue_growth
        )

        self.min_net_income_growth = float(
            min_net_income_growth
        )

    @staticmethod
    def _to_number(value):
        """
        Chuyển giá trị đầu vào về numeric.

        Giá trị không hợp lệ sẽ trở thành NaN.
        """
        return pd.to_numeric(
            pd.Series([value]),
            errors="coerce",
        ).iloc[0]

    @staticmethod
    def _is_valid_number(value) -> bool:
        """
        Kiểm tra giá trị có phải số hợp lệ hay không.

        Trả về Python bool.
        """
        return bool(
            pd.notna(value)
        )

    def check_stock(
        self,
        fundamental_row: pd.Series,
    ) -> dict:
        symbol = fundamental_row.get(
            "symbol"
        )

        report_period = fundamental_row.get(
            "report_period"
        )

        raw_revenue_growth = (
            fundamental_row.get(
                "revenue_growth"
            )
        )

        raw_net_income_growth = (
            fundamental_row.get(
                "net_income_growth"
            )
        )

        revenue_growth = self._to_number(
            raw_revenue_growth
        )

        net_income_growth = self._to_number(
            raw_net_income_growth
        )

        revenue_growth_pass = bool(
            self._is_valid_number(
                revenue_growth
            )
            and (
                float(revenue_growth)
                > self.min_revenue_growth
            )
        )

        net_income_growth_pass = bool(
            self._is_valid_number(
                net_income_growth
            )
            and (
                float(net_income_growth)
                > self.min_net_income_growth
            )
        )

        growth_pass = bool(
            revenue_growth_pass
            and net_income_growth_pass
        )

        return {
            "symbol": symbol,
            "report_period": report_period,

            "revenue_growth": revenue_growth,
            "net_income_growth": net_income_growth,

            "revenue_growth_threshold": float(
                self.min_revenue_growth
            ),

            "net_income_growth_threshold": float(
                self.min_net_income_growth
            ),

            "revenue_growth_pass": (
                revenue_growth_pass
            ),

            "net_income_growth_pass": (
                net_income_growth_pass
            ),

            "growth_pass": growth_pass,
        }

    def check_latest(
        self,
        fundamental_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra bản ghi tài chính mới nhất.
        """

        if (
            fundamental_df is None
            or fundamental_df.empty
        ):
            return {
                "symbol": None,
                "report_period": None,

                "revenue_growth": None,
                "net_income_growth": None,

                "revenue_growth_threshold": float(
                    self.min_revenue_growth
                ),

                "net_income_growth_threshold": float(
                    self.min_net_income_growth
                ),

                "revenue_growth_pass": False,
                "net_income_growth_pass": False,

                "growth_pass": False,
            }

        latest_row = (
            fundamental_df.iloc[0]
        )

        return self.check_stock(
            latest_row
        )