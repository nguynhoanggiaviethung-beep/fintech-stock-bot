import asyncio
from unittest.mock import AsyncMock, patch

import bot.telegram_bot as telegram_bot


async def run_test():
    print("=" * 60)
    print("TEST ALERT SYSTEM")
    print("=" * 60)

    # --------------------------------------------------------
    # TEST CASE:
    # Tín hiệu cũ = NO SIGNAL
    # Tín hiệu mới = BUY
    #
    # Expected:
    # Bot phải gửi Telegram alert
    # --------------------------------------------------------

    telegram_bot.subscription_state = {
        "subscriptions": {
            "123456": ["ABB"],
        },
        "last_signals": {
            "123456": {
                "ABB": "NO SIGNAL",
            }
        },
    }

    fake_result = {
        "signal": "BUY",
        "revenue_growth": 89.47,
        "net_income_growth": 379.65,
        "roe": 18.22,
        "close": 17.90,
        "price_ma20": 17.23,
        "volume_ratio": 2.50,
    }

    fake_application = AsyncMock()

    with patch(
        "bot.telegram_bot._build_signal_snapshot",
        return_value=fake_result,
    ):

        await telegram_bot._check_subscriptions(
            fake_application
        )

    # --------------------------------------------------------
    # KIỂM TRA
    # --------------------------------------------------------

    if not fake_application.bot.send_message.called:
        print("FAIL: Bot không gửi alert.")
        return

    call = (
        fake_application
        .bot
        .send_message
        .call_args
    )

    chat_id = call.kwargs.get(
        "chat_id"
    )

    message = call.kwargs.get(
        "text"
    )

    print()
    print("PASS: Bot đã gửi alert.")
    print()
    print("Chat ID:", chat_id)
    print()
    print("Message:")
    print(message)
    print()

    # Kiểm tra nội dung quan trọng

    assert chat_id == 123456
    assert "ABB" in message
    assert (
        "BUY" in message
        or "MUA" in message
    )
    assert "89.47%" in message
    assert "379.65%" in message
    assert "18.22%" in message

    # Kiểm tra trạng thái đã được cập nhật

    current_signal = (
        telegram_bot.subscription_state[
            "last_signals"
        ]["123456"]["ABB"]
    )

    assert current_signal == "BUY"

    print("PASS: Trạng thái đã được cập nhật BUY.")
    print()
    print("=" * 60)
    print("ALL ALERT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test())