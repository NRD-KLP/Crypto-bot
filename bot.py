import asyncio
import threading

from datetime import datetime, timezone

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
    save_suggestion,
)

from checker import payment_checker

from config import (
    TOKEN,
    PRICE_USDT,
    ADMIN_ID,
)

from content_manager import content_manager
from cryptopay import create_invoice
from market import get_full_market



# =========================
# MENU
# =========================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 Курсы криптовалют",
                callback_data="prices"
            )
        ],

        [
            InlineKeyboardButton(
                "💡 Предложения",
                callback_data="suggestions"
            )
        ],

        [
            InlineKeyboardButton(
                "❓ FAQ",
                callback_data="faq"
            ),

            InlineKeyboardButton(
                "👤 Профиль",
                callback_data="profile"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        keyboard
    )



def back_button(callback="back"):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data=callback
                )
            ]
        ]
    )



# =========================
# START
# =========================

async def start(update: Update, context):

    user = update.effective_user


    await add_user(
        user.id,
        user.username
    )


    await update.message.reply_text(

        "🤖 <b>Bit Ref 4U</b>\n\n"
        "Твой крипто-помощник.\n\n"
        "Выбери раздел 👇",

        parse_mode="HTML",

        reply_markup=main_menu()

    )



# =========================
# PREMIUM
# =========================

async def premium_menu(update, context):

    query = update.callback_query

    await query.answer()


    user = await get_user(
        query.from_user.id
    )


    active = False


    if user and user[4] and user[3]:

        try:

            end = datetime.fromisoformat(
                user[3]
            )


            if end.tzinfo is None:

                end = end.replace(
                    tzinfo=timezone.utc
                )


            if end > datetime.now(timezone.utc):

                active = True


        except:

            pass



    if active:

        text = (

            "💎 <b>Bit Ref 4U Premium</b>\n\n"

            "✅ Подписка активна\n\n"

            f"⏳ До:\n{user[3]}\n\n"

            "🔒 Закрытый канал\n"
            "🧩 Premium функции"

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

            "Что входит:\n\n"

            "🔒 Закрытый Premium канал\n"

            "🧩 Premium функции Mini App\n"

            "🚀 Будущие обновления\n\n"

            f"💰 Цена: <b>{PRICE_USDT} USDT</b>\n"

            "📅 Срок: <b>30 дней</b>"

        )


        keyboard = [

            [
                InlineKeyboardButton(
                    "💳 Купить",
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

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )

    )



# =========================
# BUY
# =========================

async def buy_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user


    try:

        invoice = await create_invoice(

            user_id=user.id,

            amount=PRICE_USDT

        )


        await add_invoice(

            invoice["invoice_id"],

            user.id,

            PRICE_USDT,

            "USDT"

        )


        await query.edit_message_text(

            "💳 <b>Счёт создан!</b>\n\n"

            f"💰 Цена: {PRICE_USDT} USDT\n"

            "📅 Срок: 30 дней\n\n"

            "Оплати по кнопке:",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup(

                [

                    [

                        InlineKeyboardButton(

                            "💳 Оплатить",

                            url=invoice["pay_url"]

                        )

                    ],

                    [

                        InlineKeyboardButton(

                            "🔙 Назад",

                            callback_data="premium"

                        )

                    ]

                ]

            )

        )


    except Exception as e:


        await query.edit_message_text(

            f"❌ Ошибка создания оплаты:\n{e}"

        )



# =========================
# PROFILE
# =========================

async def profile_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = await get_user(
        query.from_user.id
    )


    username = (

        f"@{query.from_user.username}"

        if query.from_user.username

        else "Не указан"

    )


    if user and user[4]:

        status = "✅ Premium активен"

        end = user[3] or "Неизвестно"


    else:

        status = "❌ Бесплатный"

        end = "Нет подписки"



    text = (

        "👤 <b>Профиль</b>\n\n"

        f"📱 Username: {username}\n"

        f"🆔 ID: <code>{query.from_user.id}</code>\n\n"

        f"💎 Статус: {status}\n"

        f"⏳ Подписка до: {end}"

    )



    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=back_button()

    )



# =========================
# PRICES
# =========================

async def prices_callback(update, context):

    query = update.callback_query

    await query.answer()


    try:

        market = await get_full_market()


        text = (

            "💰 <b>Курсы криптовалют</b>\n\n"

            f"₿ BTC: <b>${market['btc_price']:,.2f}</b>\n"

            f"Ξ ETH: <b>${market['eth_price']:,.2f}</b>\n"

            f"💎 TON: <b>${market['ton_price']:,.4f}</b>"

        )


    except Exception:

        text = (
            "❌ Ошибка получения цен."
        )



    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            [

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

        )

    )



# =========================
# SUGGESTIONS
# =========================

async def suggestions_callback(update, context):

    query = update.callback_query

    await query.answer()


    context.user_data[
        "waiting_suggestion"
    ] = True



    await query.edit_message_text(

        "💡 <b>Предложения</b>\n\n"

        "Напиши, что бы ты хотел добавить "
        "или улучшить в Bit Ref 4U.\n\n"

        "Сообщение будет отправлено разработчику.",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(

                        "❌ Отмена предложения",

                        callback_data="cancel_suggestion"

                    )

                ]

            ]

        )

    )



async def suggestion_handler(update, context):

    if not context.user_data.get(
        "waiting_suggestion"
    ):

        return



    context.user_data[
        "waiting_suggestion"
    ] = False



    user = update.effective_user



    await save_suggestion(

        user.id,

        user.username,

        update.message.text

    )



    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💡 <b>Новое предложение</b>\n\n"

            f"👤 @{user.username}\n"

            f"🆔 {user.id}\n\n"

            f"💬 {update.message.text}"

        ),

        parse_mode="HTML"

    )



    await update.message.reply_text(

        "✅ Спасибо! Предложение отправлено.",

        reply_markup=main_menu()

    )



# =========================
# FAQ
# =========================

async def faq_callback(update, context):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "❓ <b>FAQ</b>\n\n"

        "💎 Premium открывает закрытый канал.\n\n"

        "📅 Подписка действует 30 дней.\n\n"

        f"💰 Цена: {PRICE_USDT} USDT.",

        parse_mode="HTML",

        reply_markup=back_button()

    )



# =========================
# CALLBACK
# =========================

async def button_handler(update, context):

    query = update.callback_query


    if query.data == "premium":

        await premium_menu(update, context)


    elif query.data == "buy":

        await buy_callback(update, context)


    elif query.data == "prices":

        await prices_callback(update, context)


    elif query.data == "profile":

        await profile_callback(update, context)


    elif query.data == "suggestions":

        await suggestions_callback(update, context)


    elif query.data == "cancel_suggestion":

        context.user_data[
            "waiting_suggestion"
        ] = False


        await query.answer()


        await query.edit_message_text(

            "🤖 <b>Bit Ref 4U</b>\n\n"
            "Выбери раздел 👇",

            parse_mode="HTML",

            reply_markup=main_menu()

        )


    elif query.data == "faq":

        await faq_callback(update, context)


    elif query.data == "back":

        await query.answer()


        await query.edit_message_text(

            "🤖 <b>Bit Ref 4U</b>\n\n"
            "Выбери раздел 👇",

            parse_mode="HTML",

            reply_markup=main_menu()

        )



# =========================
# INIT
# =========================

async def post_init(app):

    await init_db()


    asyncio.create_task(
        payment_checker(app)
    )


    asyncio.create_task(
        content_manager(app)
    )



# =========================
# MAIN
# =========================

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

            filters.TEXT & ~filters.COMMAND,

            suggestion_handler

        )

    )


    threading.Thread(

        target=run_web,

        daemon=True

    ).start()



    print(
        "Бот запущен!"
    )


    app.run_polling()



if __name__ == "__main__":

    main()
