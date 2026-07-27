def generate_public_post(news):
    return (
        "📰 <b>Крипто-новость</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
        "#Crypto"
    )


def generate_private_post(news):
    return (
        "🔒 <b>Bit Ref 4U | Аналитика</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
        "📊 <b>Анализ:</b>\n"
        "Это событие может повлиять на настроение рынка и поведение участников.\n\n"
        "📈 <b>Возможное влияние:</b>\n"
        "Следует учитывать дальнейшее развитие ситуации и реакцию рынка.\n\n"
        "⚠️ <b>Не является финансовой рекомендацией.</b>"
    )
