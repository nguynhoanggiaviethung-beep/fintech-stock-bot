from __future__ import annotations

import pandas as pd


class FundamentalFilter:
    """
    Bộ lọc phân tích cơ bản cho chiến lược đầu tư.

    Điều kiện theo chiến lược 2 của đề bài:

    1. Revenue Growth > 15%
    2. Net Income Growth > 15%
    3. ROE > 15%

    Một cổ phiếu chỉ PASS khi đồng thời
    thỏa mãn cả 3 điều kiện.
    """

    def __init__(
        self,
        min_revenue_growth: float = 15.0,
        min_net_income_growth: float = 15.0,
        min_eps_growth: float = 15.0,
        min_roe: float = 15.0,
    ):
        self.min_revenue_growth = (
            min_revenue_growth
        )

        self.min_net_income_growth = (
            min_net_income_growth
        )

        self.min_eps_growth = min_eps_growth
        self.min_roe = min_roe

    @staticmethod
    def _is_valid_number(value) -> bool:
        """
        Kiểm tra một giá trị có phải số hợp lệ hay không.
        """

        return pd.notna(value)

    def check_stock(
        self,
        fundamental_row: pd.Series,
    ) -> dict:
        """
        Kiểm tra một cổ phiếu có đạt bộ lọc
        phân tích cơ bản hay không.

        Parameters
        ----------
        fundamental_row:
            Một dòng dữ liệu tài chính mới nhất.

        Returns
        -------
        dict
            Kết quả kiểm tra từng điều kiện
            và kết quả tổng thể.
        """

        revenue_growth = fundamental_row.get(
            "revenue_growth"
        )

        net_income_growth = fundamental_row.get(
            "net_income_growth"
        )

        roe = fundamental_row.get(
            "roe"
        )

        eps_growth = fundamental_row.get(
            "eps_growth"
        )

        # ==========================================
        # 1. KIỂM TRA REVENUE GROWTH
        # ==========================================

        revenue_growth_pass = (
            self._is_valid_number(
                revenue_growth
            )
            and revenue_growth
            > self.min_revenue_growth
        )

        # ==========================================
        # 2. KIỂM TRA NET INCOME GROWTH
        # ==========================================

        net_income_growth_pass = (
            self._is_valid_number(
                net_income_growth
            )
            and net_income_growth
            > self.min_net_income_growth
        )

        eps_growth_pass = (
            self._is_valid_number(eps_growth)
            and eps_growth >= self.min_eps_growth
        )

        # ==========================================
        # 3. KIỂM TRA ROE
        # ==========================================

        roe_pass = (
            self._is_valid_number(roe)
            and roe > self.min_roe
        )

        # ==========================================
        # 4. KẾT QUẢ TỔNG THỂ
        # ==========================================

        fundamental_pass = (
            revenue_growth_pass
            and net_income_growth_pass
            and eps_growth_pass
            and roe_pass
        )

        return {
            "symbol": fundamental_row.get(
                "symbol"
            ),

            "report_period": fundamental_row.get(
                "report_period"
            ),

            "revenue_growth": revenue_growth,

            "net_income_growth": (
                net_income_growth
            ),

            "roe": roe,

            "revenue_growth_pass": (
                revenue_growth_pass
            ),

            "net_income_growth_pass": (
                net_income_growth_pass
            ),

            "roe_pass": roe_pass,

            "fundamental_pass": (
                fundamental_pass
            ),
            "eps_growth": eps_growth,

            "eps_growth_pass": (
                eps_growth_pass
            ),
        }

    def check_latest(
        self,
        fundamental_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra dữ liệu tài chính mới nhất.

        fundamental_df phải được sắp xếp theo
        report_period giảm dần, trong đó dòng đầu
        tiên là kỳ báo cáo mới nhất.
        """

        if fundamental_df.empty:
            return {
                "symbol": None,
                "report_period": None,
                "revenue_growth": None,
                "net_income_growth": None,
                "roe": None,
                "revenue_growth_pass": False,
                "net_income_growth_pass": False,
                "roe_pass": False,
                "fundamental_pass": False,
            }

        latest_row = fundamental_df.iloc[0]

        return self.check_stock(
            latest_row
        )
