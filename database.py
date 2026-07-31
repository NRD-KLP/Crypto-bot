import aiosqlite


DB_NAME = "users.db"


async def init_db():

    async with aiosqlite.connect(DB_NAME) as db:

        # Пользователи
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                user_id INTEGER PRIMARY KEY,

                username TEXT,

                subscription_start TIMESTAMP,

                subscription_end TIMESTAMP,

                is_active INTEGER DEFAULT 0
            )
            """
        )


        # Оплаты
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (

                invoice_id INTEGER PRIMARY KEY,

                user_id INTEGER NOT NULL,

                status TEXT DEFAULT 'active',

                invite_sent INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # Новости которые уже отправлялись
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS published_news (

                link TEXT PRIMARY KEY,

                channel TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # Тексты постов
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS published_texts (

                text TEXT PRIMARY KEY,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        await db.commit()



# =========================
# USERS
# =========================


async def add_user(user_id: int, username=None):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO users
            (
                user_id,
                username
            )
            VALUES (?, ?)
            """,
            (
                user_id,
                username
            )
        )

        await db.commit()



async def get_user(user_id: int):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT
                user_id,
                username,
                subscription_start,
                subscription_end,
                is_active

            FROM users

            WHERE user_id=?
            """,
            (user_id,)
        )


        row = await cursor.fetchone()

        await cursor.close()

        return row



async def get_all_users():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT
                user_id,
                username,
                is_active,
                subscription_end

            FROM users
            """
        )


        rows = await cursor.fetchall()

        await cursor.close()

        return rows



async def activate_subscription(
        user_id,
        start,
        end
):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE users

            SET

            subscription_start=?,

            subscription_end=?,

            is_active=1


            WHERE user_id=?

            """,
            (
                start,
                end,
                user_id
            )
        )


        await db.commit()



async def deactivate_subscription(user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE users

            SET

            is_active=0

            WHERE user_id=?

            """,
            (user_id,)
        )


        await db.commit()



async def get_expired_subscriptions():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT user_id

            FROM users

            WHERE

            is_active=1

            AND

            subscription_end < CURRENT_TIMESTAMP

            """
        )


        rows = await cursor.fetchall()

        await cursor.close()


        return [
            row[0]
            for row in rows
        ]



# =========================
# INVOICES
# =========================


async def add_invoice(invoice_id, user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO invoices

            (
                invoice_id,
                user_id
            )

            VALUES (?, ?)

            """,
            (
                invoice_id,
                user_id
            )
        )


        await db.commit()



async def get_active_invoices():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT

            invoice_id,
            user_id

            FROM invoices

            WHERE status='active'

            """
        )


        rows = await cursor.fetchall()

        await cursor.close()

        return rows



async def mark_paid(invoice_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE invoices

            SET status='paid'

            WHERE invoice_id=?

            """,
            (invoice_id,)
        )


        await db.commit()



async def mark_invite_sent(invoice_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE invoices

            SET invite_sent=1

            WHERE invoice_id=?

            """,
            (invoice_id,)
        )


        await db.commit()



async def invite_sent(invoice_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT invite_sent

            FROM invoices

            WHERE invoice_id=?

            """,
            (invoice_id,)
        )


        row = await cursor.fetchone()

        await cursor.close()


        return bool(row[0]) if row else False



async def delete_invoice(invoice_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            DELETE FROM invoices

            WHERE invoice_id=?

            """,
            (invoice_id,)
        )


        await db.commit()



# =========================
# NEWS
# =========================


async def is_news_published(link, channel):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT 1

            FROM published_news

            WHERE

            link=?

            AND

            channel=?

            """,
            (
                link,
                channel
            )
        )


        result = await cursor.fetchone()

        await cursor.close()


        return result is not None



async def save_published_news(link, channel):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO published_news

            (
                link,
                channel
            )

            VALUES (?, ?)

            """,
            (
                link,
                channel
            )
        )


        await db.commit()
