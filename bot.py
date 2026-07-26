import os
import asyncio
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
CRYPTOBOT_API = "614206:AAmy1rmkZ3TOznUGJwcIJ9LfX7CnZCsjNc8"  # ВСТАВЬ СВОЙ
CHANNEL_LINK = "https://t.me/+L3n_ZyA2NsBiOTEx"     # ВСТАВЬ ССЫЛКУ
PRICE_USDT = 10

bot = Bot(token=TOKEN)
app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Это Bit Ref 4U Bot\n"
        "Купи доступ к закрытому каналу с сигналами:\n"
        "Напиши /buy, чтобы оплатить 10 USDT."
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = "https://api.crypt.bot/v1/createInvoice"
    data = {
        "asset": "USDT",
        "amount": PRICE_USDT,
        "description": f"Доступ к каналу для {user_id}",
        "payload": str(user_id)
    }
    response = requests.post(url, data=data, headers={"Crypto-Pay-API-Token": CRYPTOBOT_API})
    pay_url = response.json().get("result", {}).get("pay_url")
    await update.message.reply_text(
        f"💳 Оплати 10 USDT по ссылке:\n{pay_url}\n\n"
        "После оплаты ссылка на канал придёт автоматически."
    )

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running!"
    if request.method == "POST":
        try:
            # Инициализация Application
            application = Application.builder().token(TOKEN).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("buy", buy))
            
            # ВАЖНО: Инициализируем Application
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.initialize())
            
            # Обработка обновления
            update = Update.de_json(request.get_json(force=True), bot)
            loop.run_until_complete(application.process_update(update))
            
            # Завершаем
            loop.run_until_complete(application.shutdown())
            return "ok"
        except Exception as e:
            print(f"Ошибка: {e}")
            return "error", 500

@app.route("/cryptobot", methods=["POST"])
def cryptobot_webhook():
    data = request.get_json()
    if data.get("payload") and data.get("status") == "paid":
        user_id = int(data["payload"])
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"✅ Оплата получена! Твоя ссылка для входа в канал:\n{CHANNEL_LINK}"
            )
        except:
            pass
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
