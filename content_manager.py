import asyncio

from config import (
    PUBLIC_CHANNEL_ID,
    CHANNEL_ID,
    PUBLIC_POST_INTERVAL,
    PRIVATE_POST_INTERVAL,
)


async def public_content_manager(app):
    while True:
        try:
            await app.bot.send_message(
                chat_id=PUBLIC_CHANNEL_ID,
                text="📰 Тестовый пост в открытый канал."
            )

            print("Public post sent.")

        except Exception as e:
            print(f"Public manager error: {e}")

        await asyncio.sleep(PUBLIC_POST_INTERVAL)


async def private_content_manager(app):
    while True:
        try:
            await app.bot.send_message(
                chat_id=CHANNEL_ID,
                text="🔒 Тестовый пост в закрытый канал."
            )

            print("Private post sent.")

        except Exception as e:
            print(f"Private manager error: {e}")

        await asyncio.sleep(PRIVATE_POST_INTERVAL)
