import aiosqlite


DB_NAME = "users.db"


async def init_db():

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (

                user_id INTEGER PRIMARY KEY,
                username TEXT,

                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,

                is_active INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,

                language TEXT DEFAULT 'ru',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS invoices (

                invoice_id INTEGER PRIMARY KEY,

                user_id INTEGER NOT NULL,

                amount REAL,

                currency TEXT DEFAULT 'USDT',

                status TEXT DEFAULT 'active',

                invite_sent INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                invoice_id INTEGER,

                amount REAL,

                currency TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                username TEXT,

                message TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                referrer_id INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_news (

                link TEXT PRIMARY KEY,

                channel TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_texts (

                text TEXT PRIMARY KEY,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (

                key TEXT PRIMARY KEY,

                value TEXT
            )
        """)


        await db.commit()



# =========================
# USERS
# =========================


async def add_user(user_id, username=None):

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



async def get_user(user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT

            user_id,
            username,
            subscription_start,
            subscription_end,
            is_active,
            is_blocked,
            language

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

            SET is_active=0

            WHERE user_id=?

            """,
            (user_id,)
        )

        await db.commit()



async def is_premium(user_id):

    user = await get_user(user_id)

    if not user:
        return False

    return bool(user[4])



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



async def block_user(user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE users

            SET is_blocked=1

            WHERE user_id=?

            """,
            (user_id,)
        )

        await db.commit()



async def unblock_user(user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            UPDATE users

            SET is_blocked=0

            WHERE user_id=?

            """,
            (user_id,)
        )

        await db.commit()



async def is_blocked(user_id):

    user = await get_user(user_id)

    if not user:
        return False

    return bool(user[5])



# =========================
# INVOICES
# =========================


async def add_invoice(
        invoice_id,
        user_id,
        amount=None,
        currency="USDT"
):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO invoices

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



async def save_payment(
        user_id,
        invoice_id,
        amount,
        currency
):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT INTO payments

            (
                user_id,
                invoice_id,
                amount,
                currency
            )

            VALUES (?, ?, ?, ?)

            """,
            (
                user_id,
                invoice_id,
                amount,
                currency
            )
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



# =========================
# SUGGESTIONS
# =========================


async def save_suggestion(
        user_id,
        username,
        message
):

    async with aiosqlite.connect(DB_NAME) as db:

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
# REFERRALS
# =========================


async def add_referral(
        user_id,
        referrer_id
):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT INTO referrals

            (
                user_id,
                referrer_id
            )

            VALUES (?, ?)

            """,
            (
                user_id,
                referrer_id
            )
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



async def save_published_news(
        link,
        channel
):

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
