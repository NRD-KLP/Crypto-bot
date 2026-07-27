def generate_public_post(news):
    return (
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
    )


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
        "Новость может повлиять на настроение участников рынка.\n\n"
        "🎯 <b>Что отслеживать:</b>\n"
        "Следим за реакцией рынка."
    )
