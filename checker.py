import asyncio
from telegram.error import TelegramError

from config import CHANNEL_ID, CHECK_INTERVAL
from cryptopay import is_invoice_paid
from database import (
    get_active_invoices,
    mark_paid,
    mark_invite_sent,
    invite_sent,
    delete_invoice,
)


async def payment_checker(app):
    while True:
        try:
            invoices = await get_active_invoices()

            for invoice_id, user_id in invoices:

                # Если ссылка уже была отправлена — очищаем запись
                if await invite_sent(invoice_id):
                    await delete_invoice(invoice_id)
                    continue

                try:
                    paid = await is_invoice_paid(invoice_id)

                    if not paid:
                        continue

                    print(f"Invoice {invoice_id} paid.")

                    await mark_paid(invoice_id)

                    invite = await app.bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        member_limit=1,
                        creates_join_request=False
                    )

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "✅ Оплата получена!\n\n"
                            "Ваша одноразовая ссылка:\n\n"
                            f"{invite.invite_link}\n\n"
                            "⚠️ Ссылка действует только для одного входа."
                        )
                    )

                    await mark_invite_sent(invoice_id)

                    print(f"Invite sent to {user_id}")

                except TelegramError as e:
                    print(f"Telegram error: {e}")

                except Exception as e:
                    print(f"Invoice {invoice_id}: {e}")

        except Exception as e:
            print(f"Checker error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)