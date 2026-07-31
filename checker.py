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
    get_user,
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

                if await invite_sent(invoice_id):
                    await delete_invoice(invoice_id)
                    continue

                try:
                    paid = await is_invoice_paid(invoice_id)

                    if not paid:
                        continue

                    print(f"Invoice {invoice_id} paid.")

                    await mark_paid(invoice_id)

                    # Регистрируем пользователя
                    await add_user(user_id)

                    # ==========================================
                    # РАССЧИТЫВАЕМ СРОК PREMIUM
                    # ==========================================

                    now = datetime.now(timezone.utc)

                    user = await get_user(user_id)

                    # Если Premium ещё действует —
                    # добавляем 30 дней к существующей подписке.
                    if (
                        user
                        and user[4]
                        and user[3]
                    ):
                        try:
                            current_end = datetime.fromisoformat(
                                user[3]
                            )

                            # Если дата без timezone
                            if current_end.tzinfo is None:
                                current_end = current_end.replace(
                                    tzinfo=timezone.utc
                                )

                        except (ValueError, TypeError):
                            current_end = now

                        if current_end > now:
                            subscription_start = now
                            subscription_end = (
                                current_end
                                + timedelta(days=SUBSCRIPTION_DAYS)
                            )
                        else:
                            subscription_start = now
                            subscription_end = (
                                now
                                + timedelta(days=SUBSCRIPTION_DAYS)
                            )

                    else:
                        subscription_start = now
                        subscription_end = (
                            now
                            + timedelta(days=SUBSCRIPTION_DAYS)
                        )

                    # Активируем / продлеваем Premium
                    await activate_subscription(
                        user_id,
                        subscription_start,
                        subscription_end
                    )

                    # ==========================================
                    # СОЗДАЁМ ССЫЛКУ В КАНАЛ
                    # ==========================================

                    invite = await app.bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        member_limit=1,
                        creates_join_request=False
                    )

                    # ==========================================
                    # ОТПРАВЛЯЕМ ПОЛЬЗОВАТЕЛЮ
                    # ==========================================

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "✅ Оплата получена!\n\n"
                            "💎 Bit Ref 4U Premium активирован!\n\n"
                            f"📅 Добавлено: {SUBSCRIPTION_DAYS} дней\n"
                            f"⏳ Premium действует до: "
                            f"{subscription_end.strftime('%d.%m.%Y %H:%M')}\n\n"
                            "🔒 Вход в закрытый канал:\n\n"
                            f"{invite.invite_link}\n\n"
                            "⚠️ Ссылка предназначена только для вас."
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
                    print(
                        f"Invoice {invoice_id} processing error: {e}"
                    )

            # ==========================================
            # ПРОВЕРКА ИСТЁКШИХ ПОДПИСОК
            # ==========================================

            expired_users = await get_expired_subscriptions()

            for user_id in expired_users:

                try:
                    # Удаляем пользователя из закрытого канала
                    await app.bot.ban_chat_member(
                        chat_id=CHANNEL_ID,
                        user_id=user_id
                    )

                    # Сразу снимаем бан, чтобы пользователь
                    # мог снова попасть в канал после новой оплаты.
                    await app.bot.unban_chat_member(
                        chat_id=CHANNEL_ID,
                        user_id=user_id,
                        only_if_banned=True
                    )

                    # Отключаем Premium
                    await deactivate_subscription(user_id)

                    print(
                        f"Premium expired and access removed "
                        f"for user {user_id}"
                    )

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⏳ Ваша подписка "
                            "Bit Ref 4U Premium истекла.\n\n"
                            "🔒 Доступ к закрытому каналу отключён.\n\n"
                            "💎 Чтобы снова получить доступ, "
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
