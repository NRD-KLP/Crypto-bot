import time
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
CRYPTOBOT_API = "614206:AA8GCuCTdDCAwu4I0NDEaksYgFdwy6TfQc9"  # ВСТАВЬ СВОЙ
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
    data = {
        "asset": "USDT",
        "amount": PRICE_USDT,
        "description": f"Доступ к каналу для {user_id}",
        "payload": str(user_id)
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, data=data, headers={"Crypto-Pay-API-Token": CRYPTOBOT_API}, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    pay_url = result.get("result", {}).get("pay_url")
                    if pay_url:
                        await update.message.reply_text(
                            f"💳 Оплати 10 USDT по ссылке:\n{pay_url}\n\n"
                            "После оплаты ссылка на канал придёт автоматически."
                        )
                        return
                    else:
                        await update.message.reply_text("❌ Не удалось получить ссылку.")
                        return
                else:
                    await update.message.reply_text(f"❌ Ошибка CryptoBot: {result.get('error', 'Неизвестная ошибка')}")
                    return
            else:
                await update.message.reply_text(f"⚠️ Попытка {attempt+1}/3: статус {response.status_code}, повтор через 3 сек...")
                time.sleep(3)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Попытка {attempt+1}/3: ошибка {e}, повтор...")
            time.sleep(3)
    
    await update.message.reply_text("❌ Не удалось соединиться с CryptoBot после 3 попыток. Попробуй позже.")

# Запуск бота
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    
    print("Бот запущен на Render...")
    app.run_polling()
