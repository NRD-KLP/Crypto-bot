import os

TOKEN = os.getenv("TOKEN")
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN")

PRICE_USDT = 10

# Вставишь сюда после того, как узнаем ID канала
CHANNEL_ID = -1004323097981
PUBLIC_CHANNEL_ID = -1004341059359

PUBLIC_POST_INTERVAL = 45908675
PRIVATE_POST_INTERVAL = 20425635

# Проверка оплаты каждые N секунд
CHECK_INTERVAL = 5

CRYPTO_PAY_API = "https://pay.crypt.bot/api"

if TOKEN is None:
    raise RuntimeError("Environment variable TOKEN is not set.")

if CRYPTO_PAY_TOKEN is None:
    raise RuntimeError("Environment variable CRYPTO_PAY_TOKEN is not set.")
