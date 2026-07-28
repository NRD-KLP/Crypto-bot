import re


BAD_PHRASES = [
    "Read more",
    "Continue reading",
    "Continue Reading",
    "Read More",
    "Learn more",
    "Click here",
]


def summarize(news):
    title = news["title"].strip()
    text = news.get("description", "")

    if not text:
        return f"<b>{title}</b>"

    # Удаляем HTML
    text = re.sub(r"<.*?>", "", text)

    # Убираем лишние пробелы
    text = re.sub(r"\s+", " ", text).strip()

    # Удаляем мусорные фразы
    for phrase in BAD_PHRASES:
        text = text.replace(phrase, "")

    # Убираем повтор заголовка из описания
    if title.lower() in text.lower():
        text = text[len(title):].lstrip(".: -")

    # Красиво обрезаем
    if len(text) > 350:
        text = text[:350]

        last_dot = text.rfind(".")
        last_space = text.rfind(" ")

        if last_dot > 200:
            text = text[:last_dot + 1]
        elif last_space > 200:
            text = text[:last_space] + "..."

    return f"<b>{title}</b>\n\n{text.strip()}"
