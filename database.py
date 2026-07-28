import aiosqlite
import hashlib


DB_NAME = "users.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                invite_sent INTEGER NOT NULL DEFAULT 0,
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
                text_hash TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


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


async def is_text_published(text):
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM published_texts
            WHERE text_hash=?
            """,
            (text_hash,)
        )

        result = await cursor.fetchone()
        await cursor.close()

        return result is not None


async def save_published_text(text):
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO published_texts
            (text_hash)
            VALUES (?)
            """,
            (text_hash,)
        )

        await db.commit()
