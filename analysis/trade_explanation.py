from __future__ import annotations


class TradeExplanation:
    """
    Tạo phần giải thích cho tín hiệu giao dịch.

    Module này KHÔNG tự tính lại strategy.
    Nó chỉ đọc kết quả đã được tạo bởi SignalEngine
    và chuyển thành thông tin giải thích được.

    Mục tiêu:
    - Giải thích BUY
    - Giải thích SELL
    - Giải thích NO_SIGNAL
    - Phục vụ Telegram Bot
    - Phục vụ backtest/report
    """

    @staticmethod
    def _format_number(value, decimals=2):
        if value is None:
            return "N/A"

        try:
            return f"{float(value):.{decimals}f}"
        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def _is_true(value):
        return value is True

    def explain(self, signal_result: dict) -> dict:
        """
        Nhận kết quả từ SignalEngine.

        Trả về:
        {
            "signal": ...,
            "summary": ...,
            "reasons": [...],
            "metrics": {...},
            "execution_note": ...
        }
        """

        if signal_result is None:
            raise ValueError(
                "signal_result không được None"
            )

        signal = signal_result.get(
            "signal",
            "NO_SIGNAL",
        )

        symbol = signal_result.get(
            "symbol",
            "UNKNOWN",
        )

        reasons = []

        # ==========================================================
        # METRICS
        # ==========================================================

        roe = signal_result.get(
            "roe"
        )

        revenue_growth = signal_result.get(
            "revenue_growth"
        )

        net_income_growth = signal_result.get(
            "net_income_growth"
        )

        volume_ratio = signal_result.get(
            "volume_ratio"
        )

        close = signal_result.get(
            "close"
        )

        price_ma20 = signal_result.get(
            "price_ma20"
        )

        price_momentum = self._is_true(
            signal_result.get(
                "price_momentum"
            )
        )

        score = signal_result.get(
            "total_score"
        )

        metrics = {
            "roe": roe,
            "revenue_growth": revenue_growth,
            "net_income_growth": net_income_growth,
            "volume_ratio": volume_ratio,
            "close": close,
            "price_ma20": price_ma20,
            "price_momentum": price_momentum,
            "score": score,
        }

        # ==========================================================
        # BUY
        # ==========================================================

        if signal == "BUY":

            fundamental_pass = self._is_true(
                signal_result.get(
                    "fundamental_pass"
                )
            )

            volume_breakout = self._is_true(
                signal_result.get(
                    "volume_breakout"
                )
            )

            if fundamental_pass:

                reasons.append(
                    "Revenue Growth > 15%"
                )

                reasons.append(
                    "Net Income Growth > 15%"
                )

                reasons.append(
                    "ROE > 15%"
                )

            if volume_breakout:
                reasons.append(
                    "Volume breakout >= 1.5x "
                    "Volume MA20"
                )

            if price_momentum:
                reasons.append(
                    "Giá đóng cửa > MA20"
                )

            summary = (
                f"{symbol}: BUY"
            )

            execution_note = (
                "Tín hiệu BUY được xác định "
                "tại cuối ngày T; "
                "backtest thực hiện lệnh tại "
                "OPEN của ngày T+1."
            )

        # ==========================================================
        # SELL
        # ==========================================================

        elif signal == "SELL":

            sell_reasons = signal_result.get(
                "sell_reasons",
                [],
            )

            price_break_ma20 = self._is_true(
                signal_result.get(
                    "price_break_ma20"
                )
            )

            volume_reversal = self._is_true(
                signal_result.get(
                    "volume_reversal"
                )
            )

            if price_break_ma20:
                reasons.append(
                    "Giá đóng cửa < MA20"
                )

            if volume_reversal:
                reasons.append(
                    "Volume >= 1.5x Volume MA20 "
                    "và giá đóng cửa giảm"
                )

            # Fallback nếu SignalEngine có
            # sell_reasons nhưng không có flag.
            if not reasons and sell_reasons:
                reasons.extend(
                    sell_reasons
                )

            summary = (
                f"{symbol}: SELL"
            )

            execution_note = (
                "Tín hiệu SELL được xác định "
                "tại cuối ngày T; "
                "backtest thực hiện lệnh tại "
                "OPEN của ngày T+1."
            )

        # ==========================================================
        # NO SIGNAL
        # ==========================================================

        else:

            fundamental_pass = self._is_true(
                signal_result.get(
                    "fundamental_pass"
                )
            )

            volume_breakout = self._is_true(
                signal_result.get(
                    "volume_breakout"
                )
            )

            if not fundamental_pass:
                reasons.append(
                    "Không đạt điều kiện Fundamental: "
                    "Revenue Growth > 15%, "
                    "Net Income Growth > 15% "
                    "và ROE > 15%"
                )

            if not volume_breakout:
                reasons.append(
                    "Không đạt điều kiện Volume Breakout: "
                    "Volume chưa >= 1.5x Volume MA20"
                )

            if not price_momentum:
                reasons.append(
                    "Không đạt điều kiện Price Momentum: "
                    "Giá đóng cửa chưa > MA20"
                )

            if not reasons:
                reasons.append(
                    "Chưa có điều kiện BUY hoặc SELL phù hợp"
                )

            summary = (
                f"{symbol}: NO_SIGNAL"
            )

            execution_note = (
                "Không phát sinh lệnh."
            )

        # ==========================================================
        # HUMAN-READABLE METRICS
        # ==========================================================

        formatted_metrics = {
            "ROE": (
                f"{self._format_number(roe)}%"
                if roe is not None
                else "N/A"
            ),

            "Revenue Growth": (
                f"{self._format_number(revenue_growth)}%"
                if revenue_growth is not None
                else "N/A"
            ),

            "Net Income Growth": (
                f"{self._format_number(net_income_growth)}%"
                if net_income_growth is not None
                else "N/A"
            ),

            "Volume Ratio": (
                f"{self._format_number(volume_ratio)}x"
                if volume_ratio is not None
                else "N/A"
            ),

            "Close": (
                self._format_number(close)
                if close is not None
                else "N/A"
            ),

            "Price MA20": (
                self._format_number(price_ma20)
                if price_ma20 is not None
                else "N/A"
            ),

            "Price Momentum": (
                "PASS"
                if price_momentum
                else "FAIL"
            ),

            "Score": (
                f"{self._format_number(score, 0)}/100"
                if score is not None
                else "N/A"
            ),
        }

        return {
            "symbol": symbol,
            "signal": signal,
            "summary": summary,
            "reasons": reasons,
            "metrics": metrics,
            "formatted_metrics": formatted_metrics,
            "execution_note": execution_note,
        }

    def to_text(
        self,
        signal_result: dict,
    ) -> str:
        """
        Chuyển kết quả explanation thành text.

        Text này có thể dùng trực tiếp
        cho Telegram Bot.
        """

        explanation = self.explain(
            signal_result
        )

        lines = []

        lines.append(
            f"📊 {explanation['summary']}"
        )

        lines.append("")

        lines.append(
            "Lý do:"
        )

        for reason in explanation["reasons"]:
            lines.append(
                f"• {reason}"
            )

        lines.append("")

        lines.append(
            "Chỉ số:"
        )

        for key, value in explanation[
            "formatted_metrics"
        ].items():
            lines.append(
                f"• {key}: {value}"
            )

        lines.append("")

        lines.append(
            explanation["execution_note"]
        )

        return "\n".join(lines)