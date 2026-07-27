def generate_public_post(news, market):
    return (
        "📰 <b>Крипто-новость</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        f"😨 Fear & Greed: {market['value']} ({market['classification']})\n\n"
    )


def generate_private_post(news, market):
    return (
        "🔒 <b>Bit Ref 4U | Аналитика</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        f"😨 Индекс страха и жадности: {market['value']} ({market['classification']})\n\n"
    )
