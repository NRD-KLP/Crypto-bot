import asyncio

from datetime import datetime, timedelta, timezone

from config import (
    CHECK_INTERVAL,
    PRIVATE_CHANNEL_ID,
    SUBSCRIPTION_DAYS,
)

from cryptopay import is_invoice_paid

from database import (
    get_active_invoices,
    mark_paid,
    activate_subscription,
    get_expired_subscriptions,
    deactivate_subscription,
    mark_invite_sent,
    invite_sent,
    get_user,
    save_payment,
)


async def give_channel_access(app, user_id):

    try:

        invite_link = await app.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            member_limit=1
        )

        await app.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Оплата подтверждена!</b>\n\n"
                "💎 Bit Ref 4U Premium активирован.\n"
                "🔒 Доступ к закрытому каналу:\n\n"
                f"{invite_link.invite_link}\n\n"
                f"⏳ Срок: {SUBSCRIPTION_DAYS} дней"
            ),
            parse_mode="HTML"
        )

        return True

    except Exception as e:

        print(
            f"Invite error: {e}"
        )

        return False



async def check_payments(app):

    invoices = await get_active_invoices()

    for invoice_id, user_id in invoices:

        try:

            paid = await is_invoice_paid(
                invoice_id
            )

            if not paid:
                continue


            await mark_paid(
                invoice_id
            )


            now = datetime.now(
                timezone.utc
            )

            end = now + timedelta(
                days=SUBSCRIPTION_DAYS
            )


            await activate_subscription(
                user_id,
                now.isoformat(),
                end.isoformat()
            )


            user = await get_user(
                user_id
            )


            if user:

                await save_payment(
                    user_id,
                    invoice_id,
                    None,
                    "USDT"
                )


            if not await invite_sent(invoice_id):

                sent = await give_channel_access(
                    app,
                    user_id
                )


                if sent:

                    await mark_invite_sent(
                        invoice_id
                    )


        except Exception as e:

            print(
                f"Payment check error: {e}"
            )



async def remove_expired_users(app):

    expired = await get_expired_subscriptions()


    for user_id in expired:

        try:

            await deactivate_subscription(
                user_id
            )


            await app.bot.send_message(
                chat_id=user_id,
                text=(
                    "⏳ <b>Premium закончился.</b>\n\n"
                    "Чтобы продолжить пользоваться "
                    "Bit Ref 4U Premium — продлите подписку."
                ),
                parse_mode="HTML"
            )


        except Exception as e:

            print(
                f"Expire error: {e}"
            )



async def payment_checker(app):

    print(
        "Payment checker started"
    )


    while True:

        try:

            await check_payments(
                app
            )


            await remove_expired_users(
                app
            )


        except Exception as e:

            print(
                f"Checker error: {e}"
            )


        await asyncio.sleep(
            CHECK_INTERVAL
        )
