def generate_public_post(news):

    return (
        f"📰 <b>Крипто-новость</b>\n\n"
        f"{news['title']}\n\n"
        f"🔗 {news['link']}"
    )


def generate_private_post(news):

    return (
        f"🔒 <b>Закрытая аналитика</b>\n\n"
        f"{news['title']}\n\n"
        "Подробный анализ будет добавлен позже."
    )
