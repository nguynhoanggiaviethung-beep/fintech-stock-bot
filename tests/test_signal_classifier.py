from __future__ import annotations

from analysis.signal_classifier import (
    SignalClassifier,
)


def test_buy():
    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=True,
        total_score=100,
    )

    assert result == "BUY"

    print()
    print("BUY")
    print(result)


def test_watch():
    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=False,
        total_score=80,
    )

    assert result == "WATCH"

    print()
    print("WATCH")
    print(result)


def test_no_buy():
    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=False,
        total_score=30,
    )

    assert result == "NO_BUY"

    print()
    print("NO BUY")
    print(result)


def test_high_score_without_buy_signal():
    """
    Điểm cao nhưng Strategy 2 chưa BUY
    thì không được tự động chuyển thành BUY.
    """

    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=False,
        total_score=80,
    )

    assert result == "WATCH"

    print()
    print("HIGH SCORE BUT NO BUY SIGNAL")
    print(result)


def test_boundary_watch():
    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=False,
        total_score=50,
    )

    assert result == "WATCH"

    print()
    print("WATCH BOUNDARY")
    print(result)


def test_boundary_no_buy():
    classifier = SignalClassifier()

    result = classifier.classify(
        buy_signal=False,
        total_score=49,
    )

    assert result == "NO_BUY"

    print()
    print("NO BUY BOUNDARY")
    print(result)


if __name__ == "__main__":
    test_buy()
    test_watch()
    test_no_buy()
    test_high_score_without_buy_signal()
    test_boundary_watch()
    test_boundary_no_buy()

    print()
    print("ALL SIGNAL CLASSIFIER TESTS PASSED")