from summarizer import summarize



def generate_analysis(news):

    title = news.get(
        "title",
        "Без заголовка"
    )


    text = summarize(
        news
    )


    return (
        f"📊 <b>Анализ новости</b>\n\n"

        f"<b>{title}</b>\n\n"

        f"{text}\n\n"

        "💎 <i>Bit Ref 4U Premium</i>"
    )
