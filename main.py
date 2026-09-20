from bot.telegram_bot import create_bot


def main():

    application = create_bot()

    print("=================================")
    print("FINSTOCKVN BOT")
    print("Bot is running...")
    print("Press Ctrl+C to stop")
    print("=================================")

    application.run_polling()


if __name__ == "__main__":
    main()