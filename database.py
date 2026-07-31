import aiosqlite


DB_NAME = "users.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        # Платежи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                invite_sent INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Пользователи и Premium-подписки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Уже опубликованные новости
        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_news (
                link TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Уже опубликованные тексты
        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_texts (
                text_hash TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


# ==========================================================
# USERS / PREMIUM
# ==========================================================

async def add_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET username=excluded.username
            """,
            (user_id, username)
        )

        await db.commit()


async def activate_subscription(
    user_id: int,
    subscription_start,
    subscription_end
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO users (
                user_id,
                subscription_start,
                subscription_end,
                is_active
            )
            VALUES (?, ?, ?, 1)

            ON CONFLICT(user_id)
            DO UPDATE SET
                subscription_start=excluded.subscription_start,
                subscription_end=excluded.subscription_end,
                is_active=1
            """,
            (
                user_id,
                subscription_start,
                subscription_end
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


async def is_premium(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT is_active
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return False

        return bool(row[0])


async def deactivate_subscription(user_id: int):
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


async def get_expired_subscriptions():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT user_id
            FROM users
            WHERE is_active=1
            AND subscription_end IS NOT NULL
            AND subscription_end <= CURRENT_TIMESTAMP
            """
        )

        rows = await cursor.fetchall()
        await cursor.close()

        return [row[0] for row in rows]


# ==========================================================
# INVOICES
# ==========================================================

async def add_invoice(invoice_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO invoices
            (invoice_id, user_id)
            VALUES (?, ?)
            """,
            (invoice_id, user_id)
        )

        await db.commit()


async def get_active_invoices():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT invoice_id, user_id
            FROM invoices
            WHERE status='active'
            """
        )

        rows = await cursor.fetchall()
        await cursor.close()

        return rows


async def mark_paid(invoice_id: int):
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


async def mark_invite_sent(invoice_id: int):
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


async def invite_sent(invoice_id: int) -> bool:
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

        if row is None:
            return False

        return bool(row[0])


async def delete_invoice(invoice_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            DELETE FROM invoices
            WHERE invoice_id=?
            """,
            (invoice_id,)
        )

        await db.commit()


# ==========================================================
# PUBLISHED NEWS
# ==========================================================

async def is_news_published(link, channel):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM published_news
            WHERE link=? AND channel=?
            """,
            (link, channel)
        )

        result = await cursor.fetchone()
        await cursor.close()

        return result is not None


async def save_published_news(link, channel):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO published_news
            (link, channel)
            VALUES (?, ?)
            """,
            (link, channel)
        )

        await db.commit()


# ==========================================================
# PUBLISHED TEXTS
# ==========================================================

async def is_text_published(text_hash, channel):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM published_texts
            WHERE text_hash=? AND channel=?
            """,
            (text_hash, channel)
        )

        result = await cursor.fetchone()
        await cursor.close()

        return result is not None


async def save_published_text(text_hash, channel):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO published_texts
            (text_hash, channel)
            VALUES (?, ?)
            """,
            (text_hash, channel)
        )

        await db.commit()
