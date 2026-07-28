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
    text = news.get("description", "")

    if not text:
        return news["title"]

    # HTML
    text = re.sub(r"<.*?>", "", text)

    # Лишние пробелы
    text = re.sub(r"\s+", " ", text).strip()

    # Удаляем мусорные фразы
    for phrase in BAD_PHRASES:
        text = text.replace(phrase, "")

    # Если заголовок не повторяется — добавляем его в начало
    title = news["title"].strip()

    if title.lower() not in text.lower():
        text = f"{title}. {text}"

    # Обрезаем красиво
    if len(text) > 350:
        text = text[:350]

        last_dot = text.rfind(".")
        last_space = text.rfind(" ")

        if last_dot > 200:
            text = text[:last_dot + 1]
        elif last_space > 200:
            text = text[:last_space] + "..."

    return text.strip()
