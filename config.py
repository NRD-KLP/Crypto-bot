import os


# =========================
# TELEGRAM
# =========================

TOKEN = os.getenv(
    "TOKEN"
)

CHANNEL_ID = int(
    os.getenv(
        "CHANNEL_ID"
    )
)


# =========================
# CRYPTO PAY
# =========================

CRYPTO_PAY_TOKEN = os.getenv(
    "CRYPTO_PAY_TOKEN"
)

CRYPTO_PAY_API = (
    "https://pay.crypt.bot/api"
)


# =========================
# PREMIUM
# =========================

# Цена подписки
PRICE_USDT = 2

# Срок подписки
SUBSCRIPTION_DAYS = 30


# =========================
# ADMIN
# =========================

ADMIN_ID = 7961659998


# =========================
# POSTING
# =========================

PRIVATE_POST_INTERVAL = 7200


# =========================
# PAYMENT CHECK
# =========================

CHECK_INTERVAL = 5
