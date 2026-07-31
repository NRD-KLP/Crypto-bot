import asyncio

from datetime import datetime, timedelta, timezone

from telegram.error import TelegramError

from config import (
    CHANNEL_ID,
    CHECK_INTERVAL,
    SUBSCRIPTION_DAYS,
)

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


async def payment_checker(app):

    while True:

        try:

            # =====================================
            # ПРОВЕРКА ОПЛАТ
            # =====================================

            invoices = await get_active_invoices()


            for invoice_id, user_id in invoices:

                try:

                    # Уже обработан
                    if await invite_sent(invoice_id):
                        await delete_invoice(invoice_id)
                        continue


                    paid = await is_invoice_paid(
                        invoice_id
                    )


                    if not paid:
                        continue


                    print(
                        f"Invoice {invoice_id} paid"
                    )


                    await mark_paid(
                        invoice_id
                    )


                    # Добавляем пользователя
                    await add_user(
                        user_id
                    )


                    now = datetime.now(
                        timezone.utc
                    )


                    # ==========================
                    # ПРОДЛЕНИЕ PREMIUM
                    # ==========================

                    user = await get_user(
                        user_id
                    )


                    if (
                        user
                        and user[3]
                    ):

                        try:

                            old_end = datetime.fromisoformat(
                                user[3]
                            )


                            if old_end.tzinfo is None:
                                old_end = old_end.replace(
                                    tzinfo=timezone.utc
                                )

                        except:

                            old_end = now


                    else:

                        old_end = now



                    if old_end > now:

                        subscription_end = (
                            old_end
                            +
                            timedelta(
                                days=SUBSCRIPTION_DAYS
                            )
                        )

                    else:

                        subscription_end = (
                            now
                            +
                            timedelta(
                                days=SUBSCRIPTION_DAYS
                            )
                        )


                    await activate_subscription(
                        user_id,
                        now,
                        subscription_end
                    )


                    # Если пользователь был удалён
                    # после окончания подписки
                    try:

                        await app.bot.unban_chat_member(
                            chat_id=CHANNEL_ID,
                            user_id=user_id
                        )

                    except:

                        pass



                    # ==========================
                    # СОЗДАЁМ INVITE
                    # ==========================

                    invite = await app.bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        member_limit=1
                    )


                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "✅ <b>Оплата получена!</b>\n\n"
                            "💎 Bit Ref 4U Premium активирован.\n\n"
                            f"📅 Срок: {SUBSCRIPTION_DAYS} дней\n"
                            f"⏳ До: "
                            f"{subscription_end.strftime('%d.%m.%Y')}\n\n"
                            "🔒 Вход в закрытый канал:\n"
                            f"{invite.invite_link}"
                        ),
                        parse_mode="HTML"
                    )


                    await mark_invite_sent(
                        invoice_id
                    )


                    print(
                        f"Premium activated: {user_id}"
                    )


                except TelegramError as e:

                    print(
                        f"Telegram error: {e}"
                    )


                except Exception as e:

                    print(
                        f"Invoice error: {e}"
                    )



            # =====================================
            # ПРОВЕРКА ИСТЁКШИХ ПОДПИСОК
            # =====================================

            expired_users = await get_expired_subscriptions()


            for user_id in expired_users:


                try:

                    # Удаляем из канала

                    await app.bot.ban_chat_member(
                        chat_id=CHANNEL_ID,
                        user_id=user_id
                    )


                    await deactivate_subscription(
                        user_id
                    )


                    await app.bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⏳ <b>Ваша подписка закончилась.</b>\n\n"
                            "🔒 Доступ к Premium-каналу отключён.\n\n"
                            "Чтобы продолжить пользоваться "
                            "Bit Ref 4U Premium — оформите новую подписку."
                        ),
                        parse_mode="HTML"
                    )


                    print(
                        f"Premium expired: {user_id}"
                    )


                except TelegramError as e:

                    print(
                        f"Expire telegram error: {e}"
                    )


                except Exception as e:

                    print(
                        f"Expire error: {e}"
                    )



        except Exception as e:

            print(
                f"Checker error: {e}"
            )



        await asyncio.sleep(
            CHECK_INTERVAL
        )
