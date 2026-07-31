import aiosqlite


DB_NAME = "users.db"



async def init_db():

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            CREATE TABLE IF NOT EXISTS users (

                user_id INTEGER PRIMARY KEY,

                username TEXT,

                language TEXT DEFAULT 'ru',

                subscription_status TEXT DEFAULT 'inactive',

                subscription_end TIMESTAMP,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
            """

        )



        await db.execute(

            """
            CREATE TABLE IF NOT EXISTS invoices (

                invoice_id INTEGER PRIMARY KEY,

                user_id INTEGER NOT NULL,

                amount REAL,

                currency TEXT,

                status TEXT DEFAULT 'active',

                invite_sent INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
            """

        )



        await db.execute(

            """
            CREATE TABLE IF NOT EXISTS published_news (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                news_url TEXT UNIQUE,

                channel TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
            """

        )



        await db.execute(

            """
            CREATE TABLE IF NOT EXISTS suggestions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                username TEXT,

                message TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
            """

        )



        await db.commit()





# =========================
# USERS
# =========================


async def add_user(
        user_id,
        username=None
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


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





async def get_user(
        user_id
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        cursor = await db.execute(

            """
            SELECT *

            FROM users

            WHERE user_id = ?

            """,

            (
                user_id,
            )

        )


        return await cursor.fetchone()





async def update_language(
        user_id,
        language
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            UPDATE users

            SET language = ?

            WHERE user_id = ?

            """,

            (
                language,
                user_id
            )

        )


        await db.commit()





async def get_language(
        user_id
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        cursor = await db.execute(

            """
            SELECT language

            FROM users

            WHERE user_id = ?

            """,

            (
                user_id,
            )

        )


        result = await cursor.fetchone()



        if result:

            return result[0]


        return "ru"





# =========================
# SUGGESTIONS
# =========================


async def save_suggestion(
        user_id,
        username,
        message
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            INSERT INTO suggestions

            (
                user_id,
                username,
                message
            )

            VALUES (?, ?, ?)

            """,

            (
                user_id,
                username,
                message
            )

        )


        await db.commit()





# =========================
# INVOICES
# =========================


async def add_invoice(
        invoice_id,
        user_id,
        amount,
        currency
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            INSERT INTO invoices

            (
                invoice_id,
                user_id,
                amount,
                currency
            )

            VALUES (?, ?, ?, ?)

            """,

            (
                invoice_id,
                user_id,
                amount,
                currency
            )

        )


        await db.commit()





async def get_active_invoices():

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        cursor = await db.execute(

            """
            SELECT *

            FROM invoices

            WHERE status = 'active'

            """

        )


        return await cursor.fetchall()





async def mark_paid(
        invoice_id
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            UPDATE invoices

            SET status = 'paid'

            WHERE invoice_id = ?

            """,

            (
                invoice_id,
            )

        )


        await db.commit()





async def mark_subscription(
        user_id,
        end_date
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            UPDATE users

            SET

            subscription_status = 'active',

            subscription_end = ?

            WHERE user_id = ?

            """,

            (
                end_date,
                user_id
            )

        )


        await db.commit()





# =========================
# NEWS
# =========================


async def is_news_published(
        url,
        channel
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        cursor = await db.execute(

            """
            SELECT id

            FROM published_news

            WHERE news_url = ?

            AND channel = ?

            """,

            (
                url,
                channel
            )

        )


        return await cursor.fetchone() is not None





async def save_published_news(
        url,
        channel
):

    async with aiosqlite.connect(
        DB_NAME
    ) as db:


        await db.execute(

            """
            INSERT OR IGNORE INTO published_news

            (
                news_url,
                channel
            )

            VALUES (?, ?)

            """,

            (
                url,
                channel
            )

        )


        await db.commit()
