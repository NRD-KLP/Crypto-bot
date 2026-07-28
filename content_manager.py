import asyncio
from database import (is_news_published, save_published_news,)

from config import (
    CHANNEL_ID,
    PRIVATE_POST_INTERVAL,
)

from sources import get_latest_news
from post_generator import generate_private_post
from image_manager import get_random_image


async def content_manager(app):
    while True:
        try:
            news_list = get_latest_news()

            for news in news_list:

                if await is_news_published(news["link"], "private"):
                    continue

                print("Trying private post:", news["title"])

                text = generate_private_post(news)
                print("Private generated:", news["title"])

                await app.bot.send_message(
                    chat_id=CHANNEL_ID,
                    photo=get_random_image()
                    text=text,
                    parse_mode="HTML"
                )

                await save_published_news(news["link"], "private")

                print("Private post sent.")

                break

        except Exception as e:
            print(f"Private manager error: {e}")

        await asyncio.sleep(PRIVATE_POST_INTERVAL)
