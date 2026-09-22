import asyncio
import os

from aiohttp import web
from telegram import Update

from bot.telegram_bot import (
    create_bot,
    _post_shutdown,
    _post_init,
)


PORT = int(os.getenv("PORT", "10000"))


async def health(request):
    return web.Response(text="FINSTOCKVN BOT is running")


async def telegram_webhook(request):
    application = request.app["telegram_application"]

    data = await request.json()

    update = Update.de_json(
        data,
        application.bot,
    )

    await application.update_queue.put(update)

    return web.Response(text="OK")


async def main():
    application = create_bot()

    # Khởi tạo Telegram Application
    await application.initialize()

    # Khởi động các service của bot:
    # subscription, watchlist, portfolio, alert monitor...
    await _post_init(application)

    await application.start()

    app = web.Application()

    app["telegram_application"] = application

    # Health check cho Render
    app.router.add_get(
        "/",
        health,
    )

    # Telegram webhook endpoint
    app.router.add_post(
        "/telegram",
        telegram_webhook,
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT,
    )

    await site.start()

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if not render_url:
        print("WARNING: RENDER_EXTERNAL_URL chưa được thiết lập.")
        print("Webhook chưa được đăng ký tự động.")
    else:
        webhook_url = f"{render_url}/telegram"

        await application.bot.set_webhook(
            url=webhook_url,
        )

        print(f"Webhook URL: {webhook_url}")

    print("=================================")
    print("FINSTOCKVN BOT")
    print("Webhook mode")
    print(f"Port: {PORT}")
    print("Bot is running...")
    print("=================================")

    try:
        # Giữ Web Service chạy
        await asyncio.Event().wait()

    finally:
        print("Shutting down bot...")

        try:
            await application.bot.delete_webhook()
        except Exception as error:
            print(f"Webhook cleanup error: {error}")

        await _post_shutdown(application)

        await application.stop()
        await application.shutdown()

        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())