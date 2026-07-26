import asyncio
from telegram import Update
from telegram.ext import MessageHandler, filters
from checker import payment_checker
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TOKEN, PRICE_USDT
from cryptopay import create_invoice
from database import add_invoice


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Добро пожаловать в Bit Ref 4U!\n\n"
        f"Стоимость доступа: {PRICE_USDT} USDT\n\n"
        "Для покупки напиши /buy"
    )

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update)

app.add_handler(MessageHandler(filters.ALL, debug))


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    try:
        invoice = await create_invoice(
            user_id=user.id,
            amount=PRICE_USDT
        )

        invoice_id = invoice["invoice_id"]
        pay_url = invoice["pay_url"]

        add_invoice(invoice_id, user.id)

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
    asyncio.create_task(payment_checker(app))


def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))

    print("Бот запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()