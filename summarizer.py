import re


BAD_PHRASES = [

    "Read more",
    "Continue reading",
    "Continue Reading",
    "Read More",
    "Learn more",
    "Click here",
    "Read the full story",
    "Source:"
]


def clean_html(text):

    text = re.sub(
        r"<.*?>",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()



def remove_bad_phrases(text):

    for phrase in BAD_PHRASES:

        text = text.replace(
            phrase,
            ""
        )

    return text.strip()



def summarize(news):

    title = news.get(
        "title",
        ""
    )


    description = news.get(
        "description",
        ""
    )


    if not description:

        return title



    text = clean_html(
        description
    )


    text = remove_bad_phrases(
        text
    )


    # убираем повтор заголовка
    if title.lower() in text.lower():

        text = text.replace(
            title,
            ""
        )


    text = text.strip()



    # ограничение длины

    if len(text) > 500:

        text = text[:500]


        last_space = text.rfind(
            " "
        )


        if last_space > 300:

            text = (
                text[:last_space]
                +
                "..."
            )


    return text.strip()
