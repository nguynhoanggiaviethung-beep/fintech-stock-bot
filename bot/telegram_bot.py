import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# Load biến môi trường từ file .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# =========================
# /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "FINSTOCKVN BOT\n\n"
        "Bot phân tích tín hiệu đầu tư chứng khoán.\n\n"
        "Các lệnh hiện có:\n"
        "/start - Khởi động bot\n"
        "/signals - Xem tín hiệu hôm nay\n"
        "/signal FPT - Xem tín hiệu cổ phiếu\n"
        "/analyze FPT - Phân tích chi tiết\n"
        "/subscribe - Đăng ký cảnh báo\n"
        "/unsubscribe - Hủy cảnh báo\n"
        "/backtest - Xem kết quả backtest"
    )

    await update.message.reply_text(message)


# =========================
# /signals
# =========================

async def signals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📊 Module tín hiệu đang được phát triển."
    )


# =========================
# /signal
# =========================

async def signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/signal FPT"
        )

        return

    symbol = context.args[0].upper()

    await update.message.reply_text(
        f"🔍 Đang phân tích {symbol}..."
    )


# =========================
# /analyze
# =========================

async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Vui lòng nhập mã cổ phiếu.\n\n"
            "Ví dụ:\n"
            "/analyze FPT"
        )

        return

    symbol = context.args[0].upper()

    await update.message.reply_text(
        f"📈 Đang phân tích chi tiết {symbol}...\n"
        "Chart sẽ được tự động tạo."
    )


# =========================
# /subscribe
# =========================

async def subscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔔 Bạn đã đăng ký nhận cảnh báo tín hiệu."
    )


# =========================
# /unsubscribe
# =========================

async def unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔕 Bạn đã hủy đăng ký cảnh báo."
    )


# =========================
# /backtest
# =========================

async def backtest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📊 Module backtest đang được phát triển."
    )


# =========================
# CREATE BOT
# =========================

def create_bot():

    if not TOKEN:

        raise ValueError(
            "Không tìm thấy TELEGRAM_BOT_TOKEN "
            "trong file .env"
        )

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("signals", signals)
    )

    application.add_handler(
        CommandHandler("signal", signal)
    )

    application.add_handler(
        CommandHandler("analyze", analyze)
    )

    application.add_handler(
        CommandHandler("subscribe", subscribe)
    )

    application.add_handler(
        CommandHandler("unsubscribe", unsubscribe)
    )

    application.add_handler(
        CommandHandler("backtest", backtest)
    )

    return application