from __future__ import annotations


class ScoringEngine:
    """
    Tính điểm cho tín hiệu đầu tư.

    Tổng điểm tối đa: 100

    Quality:
        ROE > 15%                  +30

    Growth:
        Revenue Growth > 15%       +20
        Net Income Growth > 15%    +20

    Momentum:
        Volume >= 1.5 * MA20       +30
    """

    QUALITY_SCORE = 30
    REVENUE_GROWTH_SCORE = 20
    NET_INCOME_GROWTH_SCORE = 20
    MOMENTUM_SCORE = 30

    MAX_SCORE = 100

    def calculate(
        self,
        quality_pass: bool,
        revenue_growth_pass: bool,
        net_income_growth_pass: bool,
        volume_breakout: bool,
    ) -> dict:
        quality_score = (
            self.QUALITY_SCORE
            if bool(quality_pass)
            else 0
        )

        revenue_growth_score = (
            self.REVENUE_GROWTH_SCORE
            if bool(revenue_growth_pass)
            else 0
        )

        net_income_growth_score = (
            self.NET_INCOME_GROWTH_SCORE
            if bool(net_income_growth_pass)
            else 0
        )

        momentum_score = (
            self.MOMENTUM_SCORE
            if bool(volume_breakout)
            else 0
        )

        total_score = (
            quality_score
            + revenue_growth_score
            + net_income_growth_score
            + momentum_score
        )

        return {
            "quality_score": quality_score,
            "revenue_growth_score": (
                revenue_growth_score
            ),
            "net_income_growth_score": (
                net_income_growth_score
            ),
            "momentum_score": momentum_score,
            "total_score": total_score,
            "max_score": self.MAX_SCORE,
        }