import asyncio
import threading

from datetime import datetime, timezone

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

from config import (
    TOKEN,
    PRICE_USDT,
    ADMIN_ID,
)

from database import (
    init_db,
    add_user,
    get_user,
    get_language,
    update_language,
    save_suggestion,
    add_invoice,
)

from languages import get_text

from cryptopay import create_invoice

from market import get_full_market

from checker import payment_checker

from content_manager import content_manager

from web import run_web



# =========================
# LANGUAGE MENU
# =========================


def language_menu():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇷🇺 Русский",
                    callback_data="lang_ru"
                )
            ],
            [
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data="lang_en"
                )
            ],
            [
                InlineKeyboardButton(
                    "🇦🇪 العربية",
                    callback_data="lang_ar"
                )
            ],
        ]
    )



# =========================
# MAIN MENU
# =========================


def main_menu(lang):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💎 Premium",
                    callback_data="premium"
                )
            ],

            [
                InlineKeyboardButton(
                    get_text(lang, "prices"),
                    callback_data="prices"
                )
            ],

            [
                InlineKeyboardButton(
                    get_text(lang, "settings"),
                    callback_data="settings"
                )
            ],

            [
                InlineKeyboardButton(
                    get_text(lang, "profile"),
                    callback_data="profile"
                )
            ],
        ]
    )



def back_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="back"
                )
            ]
        ]
    )



# =========================
# START COMMAND
# =========================


async def start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    await add_user(
        user.id,
        user.username
    )


    language = await get_language(
        user.id
    )


    if not language:

        await update.message.reply_text(

            "🌐 Выберите язык:\n\n"
            "Choose language:\n\n"
            "اختر اللغة:",

            reply_markup=language_menu()

        )

        return



    await update.message.reply_text(

        get_text(
            language,
            "welcome"
        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            language
        )

    )



# =========================
# LANGUAGE CALLBACK
# =========================


async def language_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = query.data.split("_")[1]


    await update_language(

        query.from_user.id,

        lang

    )


    await query.edit_message_text(

        get_text(
            lang,
            "welcome"
        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            lang
        )

    )

# =========================
# SETTINGS MENU
# =========================


async def settings_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    await query.edit_message_text(

        get_text(
            lang,
            "settings"
        ),

        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(

                        get_text(
                            lang,
                            "change_language"
                        ),

                        callback_data="change_language"

                    )

                ],

                [

                    InlineKeyboardButton(

                        get_text(
                            lang,
                            "faq"
                        ),

                        callback_data="faq"

                    )

                ],

                [

                    InlineKeyboardButton(

                        get_text(
                            lang,
                            "suggestions"
                        ),

                        callback_data="suggestions"

                    )

                ],

                [

                    InlineKeyboardButton(

                        get_text(
                            lang,
                            "back"
                        ),

                        callback_data="back"

                    )

                ]

            ]

        )

    )



# =========================
# CHANGE LANGUAGE
# =========================


async def change_language_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "🌐 Выберите язык:\n\n"
        "Choose language:\n\n"
        "اختر اللغة:",

        reply_markup=language_menu()

    )



# =========================
# FAQ
# =========================


async def faq_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    if lang == "ru":

        text = (

            "❓ <b>FAQ</b>\n\n"

            "💎 Premium открывает доступ "
            "к закрытому каналу.\n\n"

            "📅 Подписка действует 30 дней.\n\n"

            "💰 Оплата производится в USDT."

        )


    elif lang == "en":

        text = (

            "❓ <b>FAQ</b>\n\n"

            "💎 Premium gives access "
            "to the private channel.\n\n"

            "📅 Subscription lasts 30 days.\n\n"

            "💰 Payment is made in USDT."

        )


    else:

        text = (

            "❓ <b>الأسئلة الشائعة</b>\n\n"

            "💎 Premium يمنحك الوصول "
            "إلى القناة الخاصة.\n\n"

            "📅 الاشتراك لمدة 30 يوماً.\n\n"

            "💰 الدفع يتم بواسطة USDT."

        )



    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=back_button()

    )



# =========================
# SUGGESTIONS
# =========================


async def suggestions_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    context.user_data[
        "waiting_suggestion"
    ] = True



    await query.edit_message_text(

        get_text(
            lang,
            "suggestion_text"
        ),

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(

                        get_text(
                            lang,
                            "cancel"
                        ),

                        callback_data="cancel_suggestion"

                    )

                ]

            ]

        )

    )



async def cancel_suggestion(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    context.user_data[
        "waiting_suggestion"
    ] = False


    lang = await get_language(
        query.from_user.id
    )


    await query.edit_message_text(

        get_text(
            lang,
            "welcome"
        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            lang
        )

    )


async def receive_suggestion(
        update,
        context
):

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


    lang = await get_language(
        user.id
    )


    await update.message.reply_text(

        "✅ Спасибо!",

        reply_markup=main_menu(
            lang
        )

    )

# =========================
# PREMIUM MENU
# =========================


async def premium_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    user = await get_user(
        query.from_user.id
    )


    status = False


    if user and user[3]:

        try:

            end_date = datetime.fromisoformat(
                user[3]
            )


            if end_date > datetime.now():

                status = True


        except:

            pass



    if status:

        text = (

            "💎 <b>Premium</b>\n\n"

            "✅ Подписка активна\n\n"

            f"⏳ До: {user[3]}"

        )


        keyboard = [

            [

                InlineKeyboardButton(

                    get_text(
                        lang,
                        "back"
                    ),

                    callback_data="back"

                )

            ]

        ]


    else:

        text = (

            "💎 <b>Bit Ref 4U Premium</b>\n\n"

            "🔒 Закрытый канал\n"

            "📊 Premium аналитика\n"

            "🚀 Новые функции\n\n"

            f"💰 Цена: {PRICE_USDT} USDT\n"

            "📅 Срок: 30 дней"

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

                    get_text(
                        lang,
                        "back"
                    ),

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
# BUY PREMIUM
# =========================


async def buy_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    try:

        invoice = await create_invoice(
            user_id=query.from_user.id,
            amount=PRICE_USDT
        )


        await add_invoice(

            invoice["invoice_id"],

            query.from_user.id,

            PRICE_USDT,

            "USDT"

        )


        await query.edit_message_text(

            "💳 <b>Счёт создан!</b>\n\n"

            f"💰 Сумма: {PRICE_USDT} USDT\n\n"

            "После оплаты доступ будет открыт автоматически.",

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

            f"❌ Ошибка создания счёта:\n{e}"

        )



# =========================
# CRYPTO PRICES
# =========================


async def prices_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    try:

        market = await get_full_market()


        text = (

            "💰 <b>Crypto Prices</b>\n\n"

            f"₿ BTC: <b>${market['btc_price']:,.2f}</b>\n"

            f"Ξ ETH: <b>${market['eth_price']:,.2f}</b>\n"

            f"💎 TON: <b>${market['ton_price']:,.4f}</b>"

        )


    except Exception:


        text = "❌ Не удалось получить цены"



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

                        get_text(
                            lang,
                            "back"
                        ),

                        callback_data="back"

                    )

                ]

            ]

        )

    )



# =========================
# PROFILE
# =========================


async def profile_callback(
        update,
        context
):

    query = update.callback_query

    await query.answer()


    lang = await get_language(
        query.from_user.id
    )


    user = await get_user(
        query.from_user.id
    )


    username = (

        f"@{query.from_user.username}"

        if query.from_user.username

        else "None"

    )


    if user and user[3]:


        status = "💎 Premium"


        end = user[3]


    else:


        status = "🆓 Free"


        end = "-"



    text = (

        f"{get_text(lang,'profile')}\n\n"

        f"👤 Username: {username}\n"

        f"🆔 ID: <code>{query.from_user.id}</code>\n\n"

        f"📌 Status: {status}\n"

        f"⏳ End: {end}"

    )



    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=back_button()

    )

# =========================
# CALLBACK HANDLER
# =========================


async def callback_handler(
        update,
        context
):

    query = update.callback_query

    data = query.data


    if data.startswith(
        "lang_"
    ):

        await language_callback(
            update,
            context
        )

        return



    if data == "premium":

        await premium_callback(
            update,
            context
        )


    elif data == "buy":

        await buy_callback(
            update,
            context
        )


    elif data == "prices":

        await prices_callback(
            update,
            context
        )


    elif data == "profile":

        await profile_callback(
            update,
            context
        )


    elif data == "settings":

        await settings_callback(
            update,
            context
        )


    elif data == "change_language":

        await change_language_callback(
            update,
            context
        )


    elif data == "faq":

        await faq_callback(
            update,
            context
        )


    elif data == "suggestions":

        await suggestions_callback(
            update,
            context
        )


    elif data == "cancel_suggestion":

        await cancel_suggestion(
            update,
            context
        )


    elif data == "back":

        await query.answer()


        lang = await get_language(
            query.from_user.id
        )


        await query.edit_message_text(

            get_text(
                lang,
                "welcome"
            ),

            parse_mode="HTML",

            reply_markup=main_menu(
                lang
            )

        )



# =========================
# BOT STARTUP
# =========================


async def post_init(
        application
):


    await init_db()



    asyncio.create_task(

        payment_checker(
            application
        )

    )



    asyncio.create_task(

        content_manager(
            application
        )

    )

async def error_handler(
        update,
        context
):

    print(
        "ERROR:",
        context.error
    )





# =========================
# MAIN
# =========================


def main():


    application = (

        Application.builder()

        .token(
            TOKEN
        )

        .post_init(
            post_init
        )

        .build()
        

    )
    application.add_error_handler(error_handler)

    application.add_handler(

        CommandHandler(
            "start",
            start
        )

    )



    application.add_handler(

        CallbackQueryHandler(
            callback_handler
        )

    )



    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            receive_suggestion

        )

    )



    threading.Thread(

        target=run_web,

        daemon=True

    ).start()



    print(
        "Bit Ref 4U started"
    )



    application.run_polling()


# =========================
# CHECK USER SUBSCRIPTION
# =========================


def check_subscription(
        user
):

    if not user:

        return False


    try:

        if user[3]:

            end_date = datetime.fromisoformat(
                user[3]
            )


            return end_date > datetime.now()


    except:

        return False



    return False



# =========================
# ADMIN COMMAND
# =========================


async def admin_test(
        update,
        context
):

    user_id = update.effective_user.id


    if user_id != ADMIN_ID:

        return


    await update.message.reply_text(

        "✅ Admin доступ работает"

    )



# =========================
# RUN
# =========================


if __name__ == "__main__":

    main()
