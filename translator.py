from deep_translator import GoogleTranslator


def translate(text):
    try:
        return GoogleTranslator(
            source="auto",
            target="ru"
        ).translate(text)
    except Exception:
        return text
