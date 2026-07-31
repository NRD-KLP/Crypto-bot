import os


def get_env(name: str, required=True):

    value = os.getenv(name)

    if required and not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value



# =========================
# TELEGRAM
# =========================

TOKEN = get_env(
    "TOKEN"
)


ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "7961659998"
    )
)


PRIVATE_CHANNEL_ID = int(
    get_env(
        "CHANNEL_ID"
    )
)



# =========================
# CRYPTOPAY
# =========================

CRYPTO_PAY_TOKEN = get_env(
    "CRYPTO_PAY_TOKEN"
)


CRYPTO_PAY_API = (
    "https://pay.crypt.bot/api"
)



# =========================
# PREMIUM
# =========================

PRICE_USDT = float(
    os.getenv(
        "PRICE_USDT",
        "2"
    )
)


SUBSCRIPTION_DAYS = int(
    os.getenv(
        "SUBSCRIPTION_DAYS",
        "30"
    )
)



# =========================
# INTERVALS
# =========================

PRIVATE_POST_INTERVAL = int(
    os.getenv(
        "PRIVATE_POST_INTERVAL",
        "10800"
    )
)


CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "10"
    )
)



# =========================
# DATABASE
# =========================

DB_NAME = "users.db"
