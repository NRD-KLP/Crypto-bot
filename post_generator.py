def generate_public_post(news):
    return (
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
    )


def generate_private_post(news):
    return (
        "🔒 <b>Bit Ref 4U | Аналитика</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
        "📊 <b>Анализ:</b>\n"
        "Событие может оказать влияние на настроение участников рынка.\n\n"
        "⚠️ <b>Важно:</b>\n"
        "Следите за дальнейшим развитием ситуации."
    )
