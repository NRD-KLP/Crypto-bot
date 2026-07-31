import asyncio
import threading

from web import run_web

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from database import (
    init_db,
    add_invoice,
    add_user,
    get_user,
)

from checker import payment_checker

from config import TOKEN, PRICE_USDT

from content_manager import content_manager
from cryptopay import create_invoice
from market import get_full_market


# ==========================================================
# ГЛАВНОЕ МЕНЮ
# ==========================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium"
            ),
        ],
        [
            InlineKeyboardButton(
                "💰 Курсы криптовалют",
                callback_data="prices"
            ),
        ],
        [
            InlineKeyboardButton(
                "⭐ Отзывы",
                callback_data="reviews"
            ),
            InlineKeyboardButton(
                "❓ FAQ",
                callback_data="faq"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ==========================================================
# /START
# ==========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    await add_user(
        user.id,
        user.username
    )

    await update.message.reply_text(
        "🤖 <b>Bit Ref 4U</b>\n\n"
        "Твой крипто-помощник.\n\n"
        "Используй меню ниже 👇",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ==========================================================
# PREMIUM
# ==========================================================

async def premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    user = await get_user(user_id)

    if user and user[4] and user[3]:

        subscription_end = user[3]

        text = (
            "💎 <b>Bit Ref 4U Premium</b>\n\n"
            "✅ Подписка активна\n\n"
            f"⏳ Действует до:\n"
            f"<b>{subscription_end}</b>\n\n"
            "Premium включает:\n"
            "🔒 Закрытый канал\n"
            "📊 Premium-инструменты\n"
            "🚀 Новые функции по мере выхода"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="back"
                )
            ]
        ]

    else:

        text = (
            "💎 <b>Bit Ref 4U Premium</b>\n\n"
            "Получишь доступ к:\n\n"
            "🔒 Закрытому каналу\n"
            "📊 Premium-инструментам\n"
            "🚀 Новым Premium-функциям\n\n"
            f"💰 Стоимость: <b>{PRICE_USDT} USDT</b>\n"
            "📅 Срок: <b>30 дней</b>"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Купить Premium",
                    callback_data="buy"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="back"
                )
            ]
        ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================================================
# ПОКУПКА PREMIUM
# ==========================================================

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    try:

        invoice = await create_invoice(
            user_id=user.id,
            amount=PRICE_USDT
        )

        invoice_id = invoice["invoice_id"]
        pay_url = invoice["pay_url"]

        await add_invoice(
            invoice_id,
            user.id
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Оплатить",
                    url=pay_url
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="premium"
                )
            ]
        ]

        await query.edit_message_text(
            "💳 <b>Счёт создан!</b>\n\n"
            f"Стоимость: <b>{PRICE_USDT} USDT</b>\n"
            "Срок: <b>30 дней</b>\n\n"
            "Нажми кнопку ниже для оплаты.\n\n"
            "После успешной оплаты Premium "
            "активируется автоматически.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:

        await query.edit_message_text(
            f"❌ Ошибка:\n{e}"
        )


# ==========================================================
# КУРСЫ
# ==========================================================

async def prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    try:
        market = await get_full_market()

        btc_price = market["btc_price"]
        btc_change = market["btc_change"]

        eth_price = market["eth_price"]
        eth_change = market["eth_change"]

        fear_value = market["value"]
        fear_classification = market["classification"]

        btc_emoji = "🟢" if btc_change >= 0 else "🔴"
        eth_emoji = "🟢" if eth_change >= 0 else "🔴"

        text = (
            "💰 <b>Крипторынок</b>\n\n"

            f"₿ <b>BTC</b>\n"
            f"${btc_price:,.2f}\n"
            f"{btc_emoji} {btc_change:+.2f}% за 24ч\n\n"

            f"Ξ <b>ETH</b>\n"
            f"${eth_price:,.2f}\n"
            f"{eth_emoji} {eth_change:+.2f}% за 24ч\n\n"

            f"😨 <b>Fear & Greed</b>\n"
            f"{fear_value} — {fear_classification}"
        )

    except Exception as e:

        print(f"Market error: {e}")

        text = (
            "❌ <b>Не удалось получить данные рынка.</b>\n\n"
            "Попробуй немного позже."
        )

    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Обновить",
                callback_data="prices"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="back"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================================================
# FAQ
# ==========================================================

async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "❓ <b>FAQ</b>\n\n"
        "💎 <b>Что такое Premium?</b>\n"
        "Premium даёт доступ к закрытому каналу "
        "и платным функциям Bit Ref 4U.\n\n"
        "📅 <b>На сколько действует подписка?</b>\n"
        "30 дней с момента оплаты.\n\n"
        "💰 <b>Сколько стоит?</b>\n"
        f"{PRICE_USDT} USDT за 30 дней.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="back"
                )
            ]
        ])
    )


# ==========================================================
# ОТЗЫВЫ
# ==========================================================

async def reviews_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "⭐ <b>Отзывы</b>\n\n"
        "🚧 Раздел отзывов будет подключён следующим этапом.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="back"
                )
            ]
        ])
    )


# ==========================================================
# CALLBACK ROUTER
# ==========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.data == "premium":
        await premium_menu(update, context)

    elif query.data == "buy":
        await buy_callback(update, context)

    elif query.data == "prices":
        await prices_callback(update, context)

    elif query.data == "faq":
        await faq_callback(update, context)

    elif query.data == "reviews":
        await reviews_callback(update, context)

    elif query.data == "back":

        await query.answer()

        await query.edit_message_text(
            "🤖 <b>Bit Ref 4U</b>\n\n"
            "Твой крипто-помощник.\n\n"
            "Используй меню ниже 👇",
            parse_mode="HTML",
            reply_markup=main_menu()
        )


# ==========================================================
# POST INIT
# ==========================================================

async def post_init(app):

    await init_db()

    payment_task = asyncio.create_task(
        payment_checker(app)
    )

    app.bot_data["payment_checker_task"] = payment_task

    private_task = asyncio.create_task(
        content_manager(app)
    )

    app.bot_data["private_content_task"] = private_task


# ==========================================================
# PHOTO ID
# ==========================================================

async def get_photo_id(update, context):

    if update.message.photo:

        photo = update.message.photo[-1]

        await update.message.reply_text(
            f"FILE_ID:\n{photo.file_id}"
        )


# ==========================================================
# MAIN
# ==========================================================

def main():

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            get_photo_id
        )
    )

    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    print("Бот запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
