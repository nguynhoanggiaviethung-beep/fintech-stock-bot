from __future__ import annotations

import pandas as pd


class QualityFilter:
    """
    Bộ lọc Quality của chiến lược đầu tư.

    Tiêu chí:
        ROE > 15%

    Quality Filter chỉ đánh giá chất lượng doanh nghiệp
    dựa trên ROE.

    Không kiểm tra:
        - Revenue Growth
        - Net Income Growth
        - Volume
        - Valuation
    """

    def __init__(
        self,
        min_roe: float = 15.0,
    ):
        self.min_roe = float(min_roe)

    @staticmethod
    def _to_number(
        value,
    ):
        """
        Chuyển giá trị đầu vào về numeric chuẩn.

        Giá trị không hợp lệ sẽ trở thành NaN.
        """

        return pd.to_numeric(
            pd.Series([value]),
            errors="coerce",
        ).iloc[0]

    @staticmethod
    def _is_valid_number(
        value,
    ) -> bool:
        """
        Trả về Python bool, không trả về numpy.bool_.
        """

        return bool(
            pd.notna(value)
        )

    def check_stock(
        self,
        fundamental_row: pd.Series,
    ) -> dict:
        """
        Kiểm tra Quality của một cổ phiếu.
        """

        symbol = fundamental_row.get(
            "symbol"
        )

        report_period = (
            fundamental_row.get(
                "report_period"
            )
        )

        # ------------------------------------------
        # ROE
        # ------------------------------------------

        raw_roe = fundamental_row.get(
            "roe"
        )

        roe = self._to_number(
            raw_roe
        )

        # ------------------------------------------
        # Quality condition
        # ------------------------------------------

        roe_pass = bool(
            self._is_valid_number(roe)
            and (
                float(roe)
                > self.min_roe
            )
        )

        quality_pass = bool(
            roe_pass
        )

        # ------------------------------------------
        # Return
        # ------------------------------------------

        return {
            "symbol": symbol,
            "report_period": report_period,
            "roe": roe,
            "roe_threshold": float(
                self.min_roe
            ),
            "roe_pass": roe_pass,
            "quality_pass": quality_pass,
        }

    def check_latest(
        self,
        fundamental_df: pd.DataFrame,
    ) -> dict:
        """
        Kiểm tra Quality dựa trên dữ liệu
        fundamental mới nhất.
        """

        if (
            fundamental_df is None
            or fundamental_df.empty
        ):
            return {
                "symbol": None,
                "report_period": None,
                "roe": None,
                "roe_threshold": float(
                    self.min_roe
                ),
                "roe_pass": False,
                "quality_pass": False,
            }

        latest_row = (
            fundamental_df.iloc[0]
        )

        return self.check_stock(
            latest_row
        )