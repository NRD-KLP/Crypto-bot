from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = "8997030652:AAHmOoA23CIwSplU5oRe9vfu_g0FeeegXkI"

async def start(update: Update, context):
    await update.message.reply_text(
        "Привет! Твой бот работает на Fly.io!\n"
        "Пиши /help для списка команд."
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "/start - приветствие\n"
        "/help - справка\n"
        "/info - информация о боте"
    )

async def info(update: Update, context):
    await update.message.reply_text(
        "Бот запущен.\n"
        "Доступен 24/7."
    )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("info", info))

print("Бот запущен...")
app.run_polling()
