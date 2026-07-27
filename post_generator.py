def generate_public_post(news):
    return (
        "📰 <b>Крипто-новость</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        "📌 Кратко:\n"
        "Главное событие дня в криптомире.\n\n"
        f"🔗 Подробнее:\n{news['link']}"
    )


def generate_private_post(news):
    return (
        "🔒 <b>Bit Ref 4U | Аналитика</b>\n\n"
        f"📰 <b>{news['title']}</b>\n\n"
        "📊 Почему это важно?\n"
        "Эта новость может повлиять на рынок. "
        "Следите за реакцией BTC и ETH в ближайшие часы.\n\n"
        "⚠️ Это информационный материал, а не финансовая рекомендация.\n\n"
        f"🔗 Источник:\n{news['link']}"
    )
