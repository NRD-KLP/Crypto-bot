from analysis_generator import generate_analysis


def generate_public_post(news):
    return (
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
        "#Crypto"
    )


def generate_private_post(news):
    analysis = generate_analysis(news)

    return (
        f"<b>{news['title']}</b>\n\n"
        f"{news['description']}\n\n"
        f"{analysis}\n\n"
        "⚠️ Не является финансовой рекомендацией."
    )
