from __future__ import annotations


class SignalClassifier:
    """
    Phân loại kết quả Signal Engine.

    Quy tắc:

        BUY:
            - Strategy 2 BUY = True
            - Tổng điểm >= 80

        WATCH:
            - Chưa đủ điều kiện BUY
            - Tổng điểm từ 50 đến 79

        NO_BUY:
            - Tổng điểm < 50

    Lưu ý:
        Score không thay thế điều kiện BUY của Strategy 2.
    """

    def __init__(
        self,
        buy_score: int = 80,
        watch_score: int = 50,
    ):
        self.buy_score = int(buy_score)
        self.watch_score = int(watch_score)

    def classify(
        self,
        buy_signal: bool,
        total_score: int,
    ) -> str:
        score = int(total_score)

        # BUY phải thỏa điều kiện Strategy 2
        # và đạt ngưỡng điểm BUY.
        if (
            bool(buy_signal)
            and score >= self.buy_score
        ):
            return "BUY"

        # Chưa BUY nhưng có mức hội tụ
        # tương đối tốt.
        if score >= self.watch_score:
            return "WATCH"

        return "NO_BUY"

    def classify_result(
        self,
        buy_signal: bool,
        total_score: int,
    ) -> dict:
        classification = self.classify(
            buy_signal=buy_signal,
            total_score=total_score,
        )

        return {
            "classification": classification,
            "total_score": int(total_score),
            "buy_score_threshold": self.buy_score,
            "watch_score_threshold": self.watch_score,
        }