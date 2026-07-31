import re



BAD_WORDS = [

    "Read more",

    "Continue reading",

    "Continue Reading",

    "Read More",

    "Learn more",

    "Click here",

    "Subscribe",

]



def clean_text(text: str):

    if not text:

        return ""



    # Удаляем HTML

    text = re.sub(
        r"<.*?>",
        "",
        text
    )



    # Удаляем мусорные фразы

    for word in BAD_WORDS:

        text = text.replace(
            word,
            ""
        )



    # Убираем лишние пробелы

    text = re.sub(
        r"\s+",
        " ",
        text
    )



    return text.strip()
