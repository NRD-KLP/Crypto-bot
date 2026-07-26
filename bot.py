import os
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
CRYPTOBOT_API = "614286:AAjNa1PW2juok3ANcHc9zcjHTHx5ty3sJ4R"
CHANNEL_LINK = "https://t.me/+L3n_ZyA2NsBiOTEx"
PRICE_USDT = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Это Bit Ref 4U Bot\n"
        "Купи доступ к закрытому каналу с сигналами:\n"
        "Напиши /buy, чтобы оплатить 10 USDT."
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = "https://pay.crypt.bot/api/createInvoice"

    data = {
        "asset": "USDT",
        "amount": PRICE_USDT,
        "description": f"Доступ к каналу для {user_id}",
        "payload": str(user_id)
    }

    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=data,
                headers=headers
            )

            await update.message.reply_text(
                f"HTTP {response.status_code}\n\n{response.text[:300]}"
            )

    except Exception as e:
        await update.message.reply_text(repr(e))

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    print("Бот запущен...")
    app.run_polling()
