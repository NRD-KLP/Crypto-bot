from summarizer import summarize


def escape_html(text: str):

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )



def generate_private_post(news):

    title = escape_html(
        news.get(
            "title",
            "Без заголовка"
        )
    )


    description = escape_html(
        summarize(
            news
        )
    )


    return (
        f"<b>{title}</b>\n\n"
        f"{description}\n\n"
        "💎 <i>Bit Ref 4U Premium</i>"
    )
