from analysis_generator import generate_analysis
from summarizer import summarize


def generate_private_post(news):
    summary = summarize(news)
    analysis = generate_analysis(news)

    return (
        f"📝 {summary}\n\n"
        f"{analysis}\n\n"
        "⚠️ Не является финансовой рекомендацией."
    )
