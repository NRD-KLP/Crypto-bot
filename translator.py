from deep_translator import GoogleTranslator



async def translate_text(
        text: str,
        language: str = "ru"
):

    try:

        translator = GoogleTranslator(
            source="auto",
            target=language
        )


        result = translator.translate(
            text
        )


        return result


    except Exception as e:

        print(
            f"Translation error: {e}"
        )

        return text
