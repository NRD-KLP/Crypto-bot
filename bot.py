import asyncio
import threading
from web import run_web
from telegram import Update
from database import init_db, add_invoice
from checker import payment_checker
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TOKEN, PRICE_USDT
from content_manager import private_content_manager
from cryptopay import create_invoice


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Добро пожаловать в Bit Ref 4U!\n\n"
        f"Стоимость доступа: {PRICE_USDT} USDT\n\n"
        "Для покупки напиши /buy"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    try:
        invoice = await create_invoice(
            user_id=user.id,
            amount=PRICE_USDT
        )

        invoice_id = invoice["invoice_id"]
        pay_url = invoice["pay_url"]

        await add_invoice(invoice_id, user.id)

        await update.message.reply_text(
            "💳 Счёт успешно создан!\n\n"
            f"Оплати его по ссылке:\n\n{pay_url}\n\n"
            "После оплаты бот автоматически выдаст доступ."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка:\n{e}"
        )


async def post_init(app):
    await init_db()

    payment_task = asyncio.create_task(payment_checker(app))
    app.bot_data["payment_checker_task"] = payment_task

    private_task = asyncio.create_task(private_content_manager(app))
    app.bot_data["private_content_task"] = private_task
    


def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))

    threading.Thread(target=run_web, daemon=True).start()

    print("Бот запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
