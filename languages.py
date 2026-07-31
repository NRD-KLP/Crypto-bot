TEXTS = {

    "ru": {

        "choose_language":
            "🌐 Выберите язык:",

        "language_changed":
            "✅ Язык успешно изменён.",

        "welcome":
            "🤖 <b>Bit Ref 4U</b>\n\n"
            "Твой крипто-помощник.\n\n"
            "Выбери раздел 👇",

        "premium":
            "💎 Premium",

        "prices":
            "💰 Курсы криптовалют",

        "settings":
            "⚙️ Настройки",

        "profile":
            "👤 Профиль",

        "change_language":
            "🌐 Смена языка",

        "faq":
            "❓ FAQ",

        "suggestions":
            "💡 Предложения",

        "back":
            "🔙 Назад",

        "suggestion_text":
            "💡 <b>Предложения</b>\n\n"
            "Напиши, что бы ты хотел добавить "
            "или улучшить в Bit Ref 4U.\n\n"
            "Сообщение будет отправлено разработчику.",

        "cancel":
            "❌ Отмена",

        "premium_active":
            "✅ Premium активен",

        "premium_inactive":
            "❌ Бесплатный аккаунт",

    },


    "en": {

        "choose_language":
            "🌐 Choose language:",

        "language_changed":
            "✅ Language changed.",

        "welcome":
            "🤖 <b>Bit Ref 4U</b>\n\n"
            "Your crypto assistant.\n\n"
            "Choose a section 👇",

        "premium":
            "💎 Premium",

        "prices":
            "💰 Crypto prices",

        "settings":
            "⚙️ Settings",

        "profile":
            "👤 Profile",

        "change_language":
            "🌐 Change language",

        "faq":
            "❓ FAQ",

        "suggestions":
            "💡 Suggestions",

        "back":
            "🔙 Back",

        "suggestion_text":
            "💡 <b>Suggestions</b>\n\n"
            "Write what you would like to add "
            "or improve in Bit Ref 4U.\n\n"
            "Your message will be sent to the developer.",

        "cancel":
            "❌ Cancel",

        "premium_active":
            "✅ Premium active",

        "premium_inactive":
            "❌ Free account",

    },


    "ar": {

        "choose_language":
            "🌐 اختر اللغة:",

        "language_changed":
            "✅ تم تغيير اللغة.",

        "welcome":
            "🤖 <b>Bit Ref 4U</b>\n\n"
            "مساعد العملات الرقمية الخاص بك.\n\n"
            "اختر القسم 👇",

        "premium":
            "💎 Premium",

        "prices":
            "💰 أسعار العملات الرقمية",

        "settings":
            "⚙️ الإعدادات",

        "profile":
            "👤 الملف الشخصي",

        "change_language":
            "🌐 تغيير اللغة",

        "faq":
            "❓ الأسئلة الشائعة",

        "suggestions":
            "💡 الاقتراحات",

        "back":
            "🔙 رجوع",

        "suggestion_text":
            "💡 <b>الاقتراحات</b>\n\n"
            "اكتب ما تريد إضافته أو تحسينه "
            "في Bit Ref 4U.\n\n"
            "سيتم إرسال رسالتك إلى المطور.",

        "cancel":
            "❌ إلغاء",

        "premium_active":
            "✅ Premium فعال",

        "premium_inactive":
            "❌ حساب مجاني",

    }

}



def get_text(language, key):

    if language not in TEXTS:

        language = "ru"


    return TEXTS[language].get(
        key,
        TEXTS["ru"].get(key, key)
    )
