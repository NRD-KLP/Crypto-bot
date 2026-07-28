from summarizer import summarize


def generate_private_post(news):
    return (
        f"{summarize(news)}\n\n"
    )
