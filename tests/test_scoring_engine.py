from __future__ import annotations

from analysis.scoring_engine import (
    ScoringEngine,
)


def test_full_score():
    engine = ScoringEngine()

    result = engine.calculate(
        quality_pass=True,
        revenue_growth_pass=True,
        net_income_growth_pass=True,
        volume_breakout=True,
    )

    assert result["quality_score"] == 30
    assert result["revenue_growth_score"] == 20
    assert result["net_income_growth_score"] == 20
    assert result["momentum_score"] == 30
    assert result["total_score"] == 100

    print()
    print("FULL SCORE")
    print(result)


def test_abb_like_score():
    engine = ScoringEngine()

    result = engine.calculate(
        quality_pass=True,
        revenue_growth_pass=True,
        net_income_growth_pass=True,
        volume_breakout=True,
    )

    assert result["total_score"] == 100

    print()
    print("ABB-LIKE SCORE")
    print(result)


def test_acb_like_score():
    engine = ScoringEngine()

    result = engine.calculate(
        quality_pass=True,
        revenue_growth_pass=False,
        net_income_growth_pass=False,
        volume_breakout=False,
    )

    assert result["total_score"] == 30

    print()
    print("ACB-LIKE SCORE")
    print(result)


def test_fpt_like_score():
    engine = ScoringEngine()

    result = engine.calculate(
        quality_pass=True,
        revenue_growth_pass=False,
        net_income_growth_pass=True,
        volume_breakout=True,
    )

    assert result["total_score"] == 80

    print()
    print("FPT-LIKE SCORE")
    print(result)


def test_no_conditions():
    engine = ScoringEngine()

    result = engine.calculate(
        quality_pass=False,
        revenue_growth_pass=False,
        net_income_growth_pass=False,
        volume_breakout=False,
    )

    assert result["total_score"] == 0

    print()
    print("NO CONDITIONS")
    print(result)


if __name__ == "__main__":
    test_full_score()
    test_abb_like_score()
    test_acb_like_score()
    test_fpt_like_score()
    test_no_conditions()

    print()
    print("ALL SCORING ENGINE TESTS PASSED")