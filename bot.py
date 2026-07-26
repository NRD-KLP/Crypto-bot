import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
CRYPTOBOT_API = "614286:AAjNa1PW2juok3ANcHc9zcjHTHx5ty3sJ4R"  # ВСТАВЬ СЮДА
CHANNEL_LINK = "https://t.me/+L3n_ZyA2NsBiOTEx"     # ВСТАВЬ ССЫЛКУ
PRICE_USDT = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Это Bit Ref 4U Bot\n"
        "Купи доступ к закрытому каналу с сигналами:\n"
        "Напиши /buy, чтобы оплатить 10 USDT."
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = "https://api.crypt.bot/v1/createInvoice"
    
    # Данные для запроса
    data = {
        "asset": "USDT",
        "amount": PRICE_USDT,
        "description": f"Доступ к каналу для {user_id}",
        "payload": str(user_id)
    }
    
    # Заголовки (ОПРЕДЕЛЕНЫ!)
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API
    }
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            pay_url = result.get("result", {}).get("pay_url")
            if pay_url:
                await update.message.reply_text(
                    f"💳 Оплати 10 USDT по ссылке:\n{pay_url}\n\n"
                    "После оплаты ссылка на канал придёт автоматически."
                )
            else:
                await update.message.reply_text("❌ Не удалось получить ссылку на оплату.")
        else:
            await update.message.reply_text(f"❌ Ошибка CryptoBot: {result.get('error', 'Неизвестная ошибка')}")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    print("Бот запущен...")
    app.run_polling()
