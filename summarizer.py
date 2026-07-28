import re


def summarize(news):
    text = news["description"]

    if not text:
        return news["title"]

    # Убираем HTML
    text = re.sub(r"<.*?>", "", text)

    # Убираем лишние пробелы
    text = re.sub(r"\s+", " ", text).strip()

    # Если описание короткое — оставляем как есть
    if len(text) <= 300:
        return text

    # Обрезаем по последнему пробелу
    short = text[:300]

    if " " in short:
        short = short[:short.rfind(" ")]

    return short + "..."
