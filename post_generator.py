from analysis_generator import generate_analysis

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
        f"{generate_analysis(news)}\n\n"
        "⚠️ <b>Не является финансовой рекомендацией.</b>"
    )
