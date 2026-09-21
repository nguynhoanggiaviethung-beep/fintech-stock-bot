import pandas as pd

from analysis.benchmark import BenchmarkAnalyzer


def test_benchmark_return():
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                ]
            ),
            "close": [
                100,
                110,
                120,
            ],
        }
    )

    result = BenchmarkAnalyzer(
        initial_value=100_000_000
    ).run(df)

    assert result["initial_value"] == 100_000_000
    assert result["final_value"] == 120_000_000

    expected_return = 20.0

    assert abs(
        result["return_pct"]
        - expected_return
    ) < 1e-9


def test_benchmark_max_drawdown():
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                ]
            ),
            "close": [
                100,
                120,
                108,
                130,
            ],
        }
    )

    result = BenchmarkAnalyzer(
        initial_value=100_000_000
    ).run(df)

    # 120 -> 108 = -10%
    assert abs(
        result["max_drawdown"]
        - (-10.0)
    ) < 1e-9


def test_empty_benchmark():
    df = pd.DataFrame(
        columns=[
            "datetime",
            "close",
        ]
    )

    result = BenchmarkAnalyzer().run(df)

    assert result["final_value"] == 100_000_000
    assert result["return_pct"] == 0.0
    assert result["max_drawdown"] == 0.0


if __name__ == "__main__":
    test_benchmark_return()
    test_benchmark_max_drawdown()
    test_empty_benchmark()

    print(
        "ALL BENCHMARK TESTS PASSED"
    )