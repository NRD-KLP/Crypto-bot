import asyncio
from datetime import datetime, timedelta, timezone

from telegram.error import TelegramError

from config import CHANNEL_ID, CHECK_INTERVAL
from cryptopay import is_invoice_paid

from database import (
    get_active_invoices,
    mark_paid,
    mark_invite_sent,
    invite_sent,
    delete_invoice,
    add_user,
    activate_subscription,
    get_expired_subscriptions,
    deactivate_subscription,
)


SUBSCRIPTION_DAYS = 30


async def payment_checker(app):
    while True:
        try:

            # ==========================================
            # ПРОВЕРКА ОПЛАТ
            # ==========================================

            invoices = await get_active_invoices()

            for invoice_id, user_id in invoices:

                # Если ссылка уже была отправлена —
                # удаляем старый invoice
                if await invite_sent(invoice_id):
                    await delete_invoice(invoice_id)
                    continue

                try:
                    paid = await is_invoice_paid(invoice_id)

                    if not paid:
                        continue

                    print(f"Invoice {invoice_id} paid.")

                    # Помечаем invoice как оплаченный
                    await mark_paid(invoice_id)

                    # Регистрируем пользователя
                    await add_user(user_id)

                    # Срок Premium — 30 дней
                    subscription_start = datetime.now(timezone.utc)
                    subscription_end = (
                        subscription_start
                        + timedelta(days=SUBSCRIPTION_DAYS)
                    )

                    # Активируем Premium
                    await activate_subscription(
                        user_id,
                        subscription_start,
                        subscription_end
                    )

                    # Создаём одноразовую ссылку
                    invite = await app.bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        member_limit=1,
                        creates_join_request=False
                    )

                    # Отправляем пользователю ссылку
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "✅ Оплата получена!\n\n"
                            "💎 Bit Ref 4U Premium активирован!\n\n"
                            f"📅 Срок подписки: {SUBSCRIPTION_DAYS} дней\n"
                            f"⏳ До: "
                            f"{subscription_end.strftime('%d.%m.%Y %H:%M')}\n\n"
                            "🔒 Ваша ссылка в закрытый канал:\n\n"
                            f"{invite.invite_link}\n\n"
                            "⚠️ Ссылка действует только для одного входа."
                        )
                    )

                    await mark_invite_sent(invoice_id)

                    print(
                        f"Premium activated for {user_id} "
                        f"until {subscription_end}"
                    )

                except TelegramError as e:
                    print(f"Telegram error: {e}")

                except Exception as e:
                    print(f"Invoice {invoice_id}: {e}")

            # ==========================================
            # ПРОВЕРКА ИСТЁКШИХ ПОДПИСОК
            # ==========================================

            expired_users = await get_expired_subscriptions()

            for user_id in expired_users:

                try:
                    await deactivate_subscription(user_id)

                    print(
                        f"Premium expired for user {user_id}"
                    )

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⏳ Ваша подписка Bit Ref 4U Premium "
                            "истекла.\n\n"
                            "Чтобы снова получить доступ к Premium, "
                            "оформите новую подписку."
                        )
                    )

                except TelegramError as e:
                    print(
                        f"Telegram error for expired user "
                        f"{user_id}: {e}"
                    )

                except Exception as e:
                    print(
                        f"Expiration error for {user_id}: {e}"
                    )

        except Exception as e:
            print(f"Checker error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)
