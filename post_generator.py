def generate_public_post(news, market):
    return (
        "📰 <b>Крипто-новость</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        "📊 <b>Рынок сейчас</b>\n"
        f"💰 BTC: ${market['btc_price']} ({market['btc_change']}%)\n"
        f"💎 ETH: ${market['eth_price']} ({market['eth_change']}%)\n\n"
        f"🔗 {news['link']}"
    )


def generate_private_post(news, market):
    return (
        "🔒 <b>Bit Ref 4U | Аналитика</b>\n\n"
        f"<b>{news['title']}</b>\n\n"
        "📊 <b>Рынок сейчас</b>\n"
        f"💰 BTC: ${market['btc_price']} ({market['btc_change']}%)\n"
        f"💎 ETH: ${market['eth_price']} ({market['eth_change']}%)\n\n"
        "⚠️ Следите за реакцией рынка после выхода новости.\n\n"
        f"🔗 {news['link']}"
    )
