import asyncio
from market import get_market_data

from config import (
    PUBLIC_CHANNEL_ID,
    CHANNEL_ID,
    PUBLIC_POST_INTERVAL,
    PRIVATE_POST_INTERVAL,
)

from sources import get_latest_news
from post_generator import (
    generate_public_post,
    generate_private_post,
)


# Уже опубликованные новости
public_published_news = set()
private_published_news = set()


async def public_content_manager(app):
    while True:
        try:
            news_list = get_latest_news()

            for news in news_list:

                if news["link"] in public_published_news:
                    continue

                market = await get_market_data()
                text = generate_public_post(news, market)

                await app.bot.send_message(
                    chat_id=PUBLIC_CHANNEL_ID,
                    text=text,
                    parse_mode="HTML"
                )

                public_published_news.add(news["link"])

                print("Public post sent.")

                break

        except Exception as e:
            print(f"Public manager error: {e}")

        await asyncio.sleep(PUBLIC_POST_INTERVAL)


async def private_content_manager(app):
    while True:
        try:
            news_list = get_latest_news()

            for news in news_list:

                if news["link"] in private_published_news:
                    continue

                market = await get_market_data()
                text = genarate_private_post(news, market)

                await app.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text,
                    parse_mode="HTML"
                )

                private_published_news.add(news["link"])

                print("Private post sent.")

                break

        except Exception as e:
            print(f"Private manager error: {e}")

        await asyncio.sleep(PRIVATE_POST_INTERVAL)
