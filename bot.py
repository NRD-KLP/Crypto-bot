"""
Bit Ref 4U — Crypto Assistant Bot (single-file build)
=======================================================

Это объединённая версия бота NRD-KLP/Crypto-bot: весь функционал исходных
17 файлов (bot.py, database.py, market.py, sources.py, summarizer.py,
post_generator.py, checker.py, content_manager.py, cryptopay.py, config.py,
languages.py, image_manager.py, translator.py, analysis_generator.py,
cleaner.py, web.py) собран в один модуль и запускается одной командой:

    python bit_ref_4u_bot.py

ЧТО ИСПРАВЛЕНО (см. подробный список в конце файла / в чате):
  1. Курсы валют: добавлены таймауты, повторные попытки, резервный источник
     (Binance) на случай сбоя/лимита CoinGecko, кэш и понятные ошибки.
  2. Посты в приватном канале: заголовок и описание теперь гарантированно
     разные (раньше при пустом RSS-description пост состоял из title дважды).
  3. Премиум расширен: портфель, ценовые алерты, конвертер, топ
     гейнеры/лузеры, индекс страха и жадности, новости на языке
     пользователя, авто-дайджест рынка в канал.
  4. Исправлены реальные баги:
       - checker.py вызывал activate_subscription(user_id, now, end) —
         3 аргумента, а функция принимала только (user_id, days). Из-за
         этого подписка НЕ активировалась в БД, и часто клиент даже не
         получал приглашение в канал после оплаты (TypeError обрывал
         остальную обработку внутри try/except).
       - save_payment вызывался с аргументами в неправильном порядке
         (invoice_id и user_id были перепутаны местами).
       - profile_callback/premium_callback/check_subscription читали
         user[3] (subscription_status, строка 'active'/'inactive') как
         дату окончания подписки (subscription_end) — из-за этого статус
         Premium мог отображаться некорректно даже неактивным юзерам.
       - переведено на aiosqlite.Row + именованные поля, чтобы больше не
         промахиваться по индексам колонок.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import aiosqlite
import feedparser
import httpx
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

try:
    from deep_translator import GoogleTranslator
except ImportError:  # переводчик опционален
    GoogleTranslator = None

try:  # удобно для локальной разработки, не обязателен в продакшене
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =========================================================================
# ЛОГИРОВАНИЕ
# =========================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("bit_ref_4u")


# =========================================================================
# CONFIG  (было config.py)
# =========================================================================

def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


# --- Telegram ---
TOKEN = get_env("TOKEN", required=True)
ADMIN_ID = int(get_env("ADMIN_ID", "7961659998"))
PRIVATE_CHANNEL_ID = int(get_env("CHANNEL_ID", required=True))

# --- CryptoPay ---
CRYPTO_PAY_TOKEN = get_env("CRYPTO_PAY_TOKEN", required=True)
CRYPTO_PAY_API = "https://pay.crypt.bot/api"

# --- Premium ---
PRICE_USDT = float(get_env("PRICE_USDT", "2"))
SUBSCRIPTION_DAYS = int(get_env("SUBSCRIPTION_DAYS", "30"))

# --- Интервалы (в секундах) ---
PRIVATE_POST_INTERVAL = int(get_env("PRIVATE_POST_INTERVAL", "10800"))     # новости в канал
CHECK_INTERVAL = int(get_env("CHECK_INTERVAL", "10"))                      # проверка оплат
ALERT_CHECK_INTERVAL = int(get_env("ALERT_CHECK_INTERVAL", "60"))          # проверка алертов
MARKET_DIGEST_INTERVAL = int(get_env("MARKET_DIGEST_INTERVAL", "21600"))   # дайджест рынка (6ч)
MARKET_CACHE_TTL = int(get_env("MARKET_CACHE_TTL", "30"))                  # кэш котировок

# --- База данных ---
DB_NAME = get_env("DB_NAME", "users.db")


# =========================================================================
# БАЗА ДАННЫХ  (было database.py)
# =========================================================================

@asynccontextmanager
async def get_db():
    """Единая точка подключения к БД, всегда с доступом по имени колонки."""
    db = await aiosqlite.connect(DB_NAME)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with get_db() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                language TEXT,
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

        # --- новые таблицы для расширенного премиум-функционала ---
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                target_price REAL NOT NULL,
                direction TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.commit()
    log.info("Database initialized")


# --- USERS -----------------------------------------------------------------

async def add_user(user_id: int, username: str | None = None):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await db.commit()


async def get_user(user_id: int) -> aiosqlite.Row | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def update_language(user_id: int, language: str):
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?", (language, user_id)
        )
        await db.commit()


async def get_language(user_id: int) -> str | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result["language"] if result else None


def is_premium_active(user: aiosqlite.Row | None) -> bool:
    """Единая, корректная проверка активной подписки (фикс путаницы user[3]/user[4])."""
    if not user:
        return False
    if user["subscription_status"] != "active":
        return False
    end = user["subscription_end"]
    if not end:
        return False
    try:
        end_date = datetime.fromisoformat(end)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        return end_date > datetime.now(timezone.utc)
    except ValueError:
        return False


# --- SUGGESTIONS -------------------------------------------------------------

async def save_suggestion(user_id: int, username: str | None, message: str):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO suggestions (user_id, username, message) VALUES (?, ?, ?)",
            (user_id, username, message),
        )
        await db.commit()


# --- INVOICES / PAYMENTS ------------------------------------------------------

async def add_invoice(invoice_id: int, user_id: int, amount: float, currency: str):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO invoices (invoice_id, user_id, amount, currency)
            VALUES (?, ?, ?, ?)
            """,
            (invoice_id, user_id, amount, currency),
        )
        await db.commit()


async def get_active_invoices():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM invoices WHERE status = 'active'")
        return await cursor.fetchall()


async def mark_paid(invoice_id: int):
    async with get_db() as db:
        await db.execute(
            "UPDATE invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,)
        )
        await db.commit()


async def mark_invite_sent(invoice_id: int):
    async with get_db() as db:
        await db.execute(
            "UPDATE invoices SET invite_sent = 1 WHERE invoice_id = ?", (invoice_id,)
        )
        await db.commit()


async def invite_sent(invoice_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT invite_sent FROM invoices WHERE invoice_id = ?", (invoice_id,)
        )
        result = await cursor.fetchone()
        return bool(result and result["invite_sent"] == 1)


async def save_payment(invoice_id: int, user_id: int, amount: float | None, currency: str):
    """ФИКС: раньше checker.py вызывал эту функцию с перепутанными местами
    invoice_id и user_id, из-за чего UPDATE ... WHERE invoice_id = ? AND
    user_id = ? никогда не находил строку и платёж не помечался."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE invoices
            SET status = 'paid', amount = COALESCE(?, amount), currency = ?
            WHERE invoice_id = ? AND user_id = ?
            """,
            (amount, currency, invoice_id, user_id),
        )
        await db.commit()


# --- SUBSCRIPTION --------------------------------------------------------------

async def mark_subscription(user_id: int, end_date_iso: str):
    async with get_db() as db:
        await db.execute(
            """
            UPDATE users
            SET subscription_status = 'active', subscription_end = ?
            WHERE user_id = ?
            """,
            (end_date_iso, user_id),
        )
        await db.commit()


async def activate_subscription(user_id: int, days: int = SUBSCRIPTION_DAYS):
    """ФИКС: единственная и явная сигнатура (user_id, days). checker.py
    раньше вызывал эту функцию с тремя позиционными аргументами
    (user_id, now.isoformat(), end.isoformat()), что вызывало TypeError
    и обрывало обработку платежа до отправки приглашения в канал."""
    end_date = datetime.now(timezone.utc) + timedelta(days=days)
    await mark_subscription(user_id, end_date.isoformat())
    return end_date


async def deactivate_subscription(user_id: int):
    async with get_db() as db:
        await db.execute(
            """
            UPDATE users
            SET subscription_status = 'inactive', subscription_end = NULL
            WHERE user_id = ?
            """,
            (user_id,),
        )
        await db.commit()


async def get_expired_subscriptions():
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT user_id FROM users
            WHERE subscription_status = 'active' AND subscription_end < ?
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )
        rows = await cursor.fetchall()
        return [row["user_id"] for row in rows]


# --- NEWS ------------------------------------------------------------------

async def is_news_published(url: str, channel: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM published_news WHERE news_url = ? AND channel = ?",
            (url, channel),
        )
        return await cursor.fetchone() is not None


async def save_published_news(url: str, channel: str):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO published_news (news_url, channel) VALUES (?, ?)",
            (url, channel),
        )
        await db.commit()


# --- PORTFOLIO (новое) -------------------------------------------------------

async def add_holding(user_id: int, symbol: str, amount: float):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO portfolio (user_id, symbol, amount) VALUES (?, ?, ?)",
            (user_id, symbol.upper(), amount),
        )
        await db.commit()


async def get_portfolio(user_id: int):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM portfolio WHERE user_id = ? ORDER BY id", (user_id,)
        )
        return await cursor.fetchall()


async def clear_portfolio(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM portfolio WHERE user_id = ?", (user_id,))
        await db.commit()


# --- PRICE ALERTS (новое) ----------------------------------------------------

async def add_alert(user_id: int, symbol: str, target_price: float, direction: str):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO price_alerts (user_id, symbol, target_price, direction)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, symbol.upper(), target_price, direction),
        )
        await db.commit()


async def get_active_alerts():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM price_alerts WHERE active = 1")
        return await cursor.fetchall()


async def get_user_alerts(user_id: int):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM price_alerts WHERE user_id = ? AND active = 1 ORDER BY id",
            (user_id,),
        )
        return await cursor.fetchall()


async def deactivate_alert(alert_id: int):
    async with get_db() as db:
        await db.execute(
            "UPDATE price_alerts SET active = 0 WHERE id = ?", (alert_id,)
        )
        await db.commit()


async def clear_alerts(user_id: int):
    async with get_db() as db:
        await db.execute(
            "UPDATE price_alerts SET active = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


# =========================================================================
# РЫНОК / КУРСЫ  (было market.py) — ИСПРАВЛЕНО
# =========================================================================
#
# Проблема оригинала: один HTTP-запрос без таймаута, без повторов и без
# обработки ошибок. Как только CoinGecko отвечал 429 (rate limit) или
# отдавал пустой/иной JSON, .get(coin_id, {}).get("usd", 0) тихо
# возвращал 0 — бот показывал курс "$0.00" или не показывал вовсе,
# и это выглядело как "иногда работает правильно, иногда нет".
#
# Исправлено:
#   - таймауты + до 3 повторных попыток с задержкой;
#   - резервный источник (Binance public API), если CoinGecko недоступен;
#   - кэш на MARKET_CACHE_TTL секунд, чтобы не упираться в rate limit;
#   - расширенный список монет + 24ч изменение цены.

SUPPORTED_COINS = {
    "BTC":  {"id": "bitcoin",           "binance": "BTCUSDT",  "name": "Bitcoin"},
    "ETH":  {"id": "ethereum",          "binance": "ETHUSDT",  "name": "Ethereum"},
    "TON":  {"id": "the-open-network",  "binance": "TONUSDT",  "name": "Toncoin"},
    "BNB":  {"id": "binancecoin",       "binance": "BNBUSDT",  "name": "BNB"},
    "SOL":  {"id": "solana",            "binance": "SOLUSDT",  "name": "Solana"},
    "XRP":  {"id": "ripple",            "binance": "XRPUSDT",  "name": "XRP"},
    "ADA":  {"id": "cardano",           "binance": "ADAUSDT",  "name": "Cardano"},
    "DOGE": {"id": "dogecoin",          "binance": "DOGEUSDT", "name": "Dogecoin"},
    "TRX":  {"id": "tron",              "binance": "TRXUSDT",  "name": "TRON"},
    "LTC":  {"id": "litecoin",          "binance": "LTCUSDT",  "name": "Litecoin"},
}

COINGECKO_API = "https://api.coingecko.com/api/v3"
BINANCE_API = "https://api.binance.com/api/v3"
FNG_API = "https://api.alternative.me/fng/"

_market_cache: dict = {"data": None, "ts": 0.0}
_market_lock = asyncio.Lock()


def format_price(value: float) -> str:
    if value == 0:
        return "0.00"
    if value >= 1:
        return f"{value:,.2f}"
    return f"{value:,.6f}"


async def _fetch_coingecko() -> dict:
    ids = ",".join(info["id"] for info in SUPPORTED_COINS.values())
    url = f"{COINGECKO_API}/simple/price"
    params = {"ids": ids, "vs_currencies": "usd", "include_24hr_change": "true"}

    last_error = None
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(3):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not data:
                    raise ValueError("Empty/invalid response from CoinGecko")

                result = {}
                for symbol, info in SUPPORTED_COINS.items():
                    coin_data = data.get(info["id"])
                    if not coin_data or "usd" not in coin_data:
                        continue
                    result[symbol] = {
                        "price": float(coin_data["usd"]),
                        "change_24h": float(coin_data.get("usd_24h_change") or 0),
                    }
                if not result:
                    raise ValueError("CoinGecko returned no usable prices")
                return result

            except (httpx.HTTPError, ValueError, json.JSONDecodeError) as e:
                last_error = e
                log.warning("CoinGecko attempt %s failed: %s", attempt + 1, e)
                await asyncio.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"CoinGecko unavailable: {last_error}")


async def _fetch_binance_fallback() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:

        async def fetch_one(symbol, info):
            try:
                resp = await client.get(
                    f"{BINANCE_API}/ticker/24hr",
                    params={"symbol": info["binance"]},
                )
                resp.raise_for_status()
                data = resp.json()
                return symbol, {
                    "price": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"]),
                }
            except Exception as e:
                log.warning("Binance fallback failed for %s: %s", symbol, e)
                return symbol, None

        results = await asyncio.gather(
            *(fetch_one(sym, info) for sym, info in SUPPORTED_COINS.items())
        )

    market = {sym: data for sym, data in results if data is not None}
    if not market:
        raise RuntimeError("Binance fallback also unavailable")
    return market


async def get_full_market(force: bool = False) -> dict:
    """Возвращает {"BTC": {"price": ..., "change_24h": ...}, ...} с кэшем и
    резервным источником. Бросает RuntimeError только если оба источника
    недоступны И в кэше вообще ничего нет."""

    now = time.time()
    if not force and _market_cache["data"] and (now - _market_cache["ts"] < MARKET_CACHE_TTL):
        return _market_cache["data"]

    async with _market_lock:
        # повторная проверка кэша — другой таск мог уже обновить, пока мы ждали лок
        now = time.time()
        if not force and _market_cache["data"] and (now - _market_cache["ts"] < MARKET_CACHE_TTL):
            return _market_cache["data"]

        try:
            data = await _fetch_coingecko()
        except Exception as e:
            log.error("Primary market source failed, trying fallback: %s", e)
            try:
                data = await _fetch_binance_fallback()
            except Exception as e2:
                log.error("All market sources failed: %s", e2)
                if _market_cache["data"]:
                    log.warning("Serving stale cached market data")
                    return _market_cache["data"]
                raise RuntimeError("Не удалось получить курсы ни из одного источника") from e2

        _market_cache["data"] = data
        _market_cache["ts"] = time.time()
        return data


async def get_price(symbol: str) -> float:
    market = await get_full_market()
    coin = market.get(symbol.upper())
    return coin["price"] if coin else 0.0


async def get_top_movers(limit: int = 5):
    """Топ гейнеров/лузеров за 24ч среди поддерживаемых монет."""
    market = await get_full_market()
    ranked = sorted(market.items(), key=lambda kv: kv[1]["change_24h"], reverse=True)
    gainers = ranked[:limit]
    losers = ranked[-limit:][::-1]
    return gainers, losers


async def get_fear_greed():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(FNG_API, params={"limit": 1})
            resp.raise_for_status()
            data = resp.json()
            item = data["data"][0]
            return {
                "value": int(item["value"]),
                "classification": item["value_classification"],
            }
        except Exception as e:
            log.warning("Fear & Greed fetch failed: %s", e)
            return None


async def convert_amount(amount: float, from_symbol: str, to_symbol: str) -> float | None:
    """Конвертация между поддерживаемыми монетами и USD через мост в USD."""
    from_symbol = from_symbol.upper()
    to_symbol = to_symbol.upper()
    market = await get_full_market()

    if from_symbol == "USD" and to_symbol in market:
        return amount / market[to_symbol]["price"]
    if to_symbol == "USD" and from_symbol in market:
        return amount * market[from_symbol]["price"]
    if from_symbol in market and to_symbol in market:
        usd_value = amount * market[from_symbol]["price"]
        return usd_value / market[to_symbol]["price"]
    return None


# =========================================================================
# НОВОСТИ: ИСТОЧНИКИ / СУММАРИЗАЦИЯ / ПОСТЫ
# (было sources.py + summarizer.py + cleaner.py + post_generator.py +
#  analysis_generator.py) — ИСПРАВЛЕНО дублирование заголовка/описания
# =========================================================================

NEWS_SOURCES = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://cryptoslate.com/feed/",
]

BAD_PHRASES = [
    "Read more", "Continue reading", "Continue Reading", "Read More",
    "Learn more", "Click here", "Read the full story", "Source:", "Subscribe",
]


def _extract_raw_description(entry) -> str:
    """ФИКС: у части RSS-лент (например Cointelegraph) поле 'description'
    пустое или дублирует заголовок, а реальный текст лежит в 'summary' или
    'content'. Раньше брали только 'description', из-за чего summarize()
    падал на ветку `if not description: return title`, и пост состоял из
    заголовка, повторённого дважды."""
    for key in ("summary", "description"):
        value = entry.get(key)
        if value and value.strip():
            return value
    content = entry.get("content")
    if content and isinstance(content, list) and content:
        value = content[0].get("value", "")
        if value and value.strip():
            return value
    return ""


def get_latest_news(per_source: int = 5):
    news_list = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source)
            for item in feed.entries[:per_source]:
                news_list.append(
                    {
                        "title": item.get("title", "Без заголовка"),
                        "description": _extract_raw_description(item),
                        "link": item.get("link", ""),
                    }
                )
        except Exception as e:
            log.warning("RSS error %s: %s", source, e)
    return news_list


def clean_html(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_bad_phrases(text: str) -> str:
    for phrase in BAD_PHRASES:
        text = text.replace(phrase, "")
    return text.strip()


FALLBACK_TEASERS = [
    "Свежий инфоповод на крипторынке — детали от источника пока не опубликованы, следим за реакцией цены.",
    "Только что вышедшая новость. Разбор и влияние на рынок — в следующих обновлениях канала.",
    "Событие может повлиять на настроение рынка в ближайшие часы — держим вас в курсе в этом канале.",
]


def summarize(news: dict, max_len: int = 500) -> str:
    title = (news.get("title") or "").strip()
    raw_description = news.get("description") or ""

    text = clean_html(raw_description)
    text = remove_bad_phrases(text)

    # убираем повтор заголовка в начале описания
    if title and text.lower().startswith(title.lower()):
        text = text[len(title):].strip(" -–—:|\n")

    # ФИКС: если после очистки описание пустое ИЛИ оно фактически совпадает
    # с заголовком (некоторые ленты дублируют title в description целиком),
    # больше НЕ возвращаем title как псевдо-описание — иначе заголовок и
    # текст поста были бы идентичны. Вместо этого — нейтральный тизер.
    if not text or text.lower() == title.lower():
        text = random.choice(FALLBACK_TEASERS)

    if len(text) > max_len:
        text = text[:max_len]
        last_space = text.rfind(" ")
        if last_space > 300:
            text = text[:last_space] + "..."

    return text.strip()


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_private_post(news: dict) -> str:
    """ФИКС: заголовок (жирный, с эмодзи 📰) и описание (курсивом, отдельным
    блоком) теперь визуально и содержательно различаются — раньше пост
    выглядел как "заголовок / тот же заголовок".

    ВАЖНО: ссылка на источник и его домен намеренно НЕ публикуются в посте.
    Раньше тизер для новостей без своего описания говорил "подробнее по
    ссылке" и показывал домен источника (например coindesk.com) — это
    фактически подсказывало подписчикам, где бесплатно прочитать ту же
    новость, обесценивая платную подписку. Теперь весь контент поста
    самодостаточен и никуда не отправляет читателя."""
    title = escape_html(news.get("title", "Без заголовка"))
    summary = escape_html(summarize(news))

    return (
        f"📰 <b>{title}</b>\n\n"
        f"<i>{summary}</i>\n\n"
        "💎 <i>Bit Ref 4U Premium</i>"
    )


def generate_analysis(news: dict) -> str:
    title = escape_html(news.get("title", "Без заголовка"))
    text = escape_html(summarize(news))
    return (
        "📊 <b>Анализ новости</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{text}\n\n"
        "💎 <i>Bit Ref 4U Premium</i>"
    )


async def generate_market_digest() -> str | None:
    """Новое: ежедневный дайджест рынка для приватного канала — курсы,
    топ движения за 24ч и индекс страха/жадности одним постом."""
    try:
        market = await get_full_market()
    except Exception as e:
        log.error("Digest: market unavailable: %s", e)
        return None

    gainers, losers = await get_top_movers(3)
    fng = await get_fear_greed()

    lines = ["📊 <b>Рыночный дайджест Bit Ref 4U</b>\n"]
    lines.append("💰 <b>Курсы:</b>")
    for symbol in ("BTC", "ETH", "TON"):
        coin = market.get(symbol)
        if coin:
            arrow = "🟢" if coin["change_24h"] >= 0 else "🔴"
            lines.append(
                f"{arrow} {symbol}: ${format_price(coin['price'])} "
                f"({coin['change_24h']:+.2f}% за 24ч)"
            )

    lines.append("\n🚀 <b>Топ роста:</b>")
    for symbol, data in gainers:
        lines.append(f"  {symbol}: {data['change_24h']:+.2f}%")

    lines.append("\n📉 <b>Топ падения:</b>")
    for symbol, data in losers:
        lines.append(f"  {symbol}: {data['change_24h']:+.2f}%")

    if fng:
        lines.append(f"\n😨 <b>Индекс страха и жадности:</b> {fng['value']} ({fng['classification']})")

    lines.append("\n💎 <i>Bit Ref 4U Premium</i>")
    return "\n".join(lines)


# =========================================================================
# ПЕРЕВОДЧИК (было translator.py) — использован в новой фиче "новости на языке"
# =========================================================================

async def translate_text(text: str, language: str = "ru") -> str:
    if not text or not GoogleTranslator or language == "ru":
        return text
    try:
        # deep_translator синхронный — уводим в отдельный поток, чтобы не
        # блокировать event loop бота (в исходнике вызывался напрямую).
        return await asyncio.to_thread(
            lambda: GoogleTranslator(source="auto", target=language).translate(text)
        )
    except Exception as e:
        log.warning("Translation error: %s", e)
        return text


# =========================================================================
# CRYPTOPAY  (было cryptopay.py)
# =========================================================================

CRYPTO_PAY_HEADERS = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}


async def create_invoice(user_id: int, amount: float, currency: str = "USDT") -> dict:
    url = f"{CRYPTO_PAY_API}/createInvoice"
    payload = {
        "asset": currency,
        "amount": str(amount),
        "description": f"Bit Ref 4U Premium {SUBSCRIPTION_DAYS} days | User {user_id}",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=CRYPTO_PAY_HEADERS, json=payload)
        data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay createInvoice failed: {data}")

    result = data["result"]
    return {
        "invoice_id": result["invoice_id"],
        "pay_url": result.get("bot_invoice_url") or result.get("mini_app_invoice_url"),
    }


async def get_invoice(invoice_id: int) -> dict | None:
    url = f"{CRYPTO_PAY_API}/getInvoices"
    params = {"invoice_ids": invoice_id}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=CRYPTO_PAY_HEADERS, params=params)
        data = response.json()

    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay getInvoices failed: {data}")

    invoices = data["result"]["items"]
    return invoices[0] if invoices else None


async def is_invoice_paid(invoice_id: int) -> bool:
    invoice = await get_invoice(invoice_id)
    return bool(invoice and invoice["status"] == "paid")


# =========================================================================
# ИЗОБРАЖЕНИЯ  (было image_manager.py)
# =========================================================================
# ВАЖНО: эти file_id привязаны к оригинальному боту/токену. При смене
# токена бота Telegram, скорее всего, эти file_id перестанут быть валидны —
# get_random_post_photo() ниже подстрахован try/except в вызывающем коде
# (см. content_manager) и в случае ошибки отправит пост без фото.

IMAGES = [
    "AgACAgIAAxkBAAICImpoP92p2UhMoCpfBIICcOjOVdujAAJTHGsbSoNBS0N3C8QRFpMWAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAICJGpoP-GrGI6DQLdrUGDerPZRj9s0AAJUHGsbSoNBS_2Gzzkb0ZZQAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAICJmpoP-Xpykxp7LVd8hCgMbIHc1_gAAJVHGsbSoNBS4jrEzDVWdbsAQADAgADeAADPQQ",
    "AgACAgIAAxkBAAICKGpoP-gXCGSt8IzCeU0l8QHYxm34AAJWHGsbSoNBS2xfayCty6skAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAICKmpoP-tyIpYOCXv-hZKoGPjFXCYlAAJXHGsbSoNBS1IY_JWNd3LMAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAICLGpoP_DGdEaDIBYl5y_FSbPA5ZtxAAJYHGsbSoNBSynnFCwjpfY5AQADAgADeQADPQQ",
]


def get_random_image() -> str:
    return random.choice(IMAGES)


# =========================================================================
# ЯЗЫКИ / ТЕКСТЫ  (было languages.py)
# =========================================================================

TEXTS = {
    "ru": {
        "welcome": "🤖 <b>Bit Ref 4U</b>\n\nТвой крипто-помощник.\n\nВыбери раздел 👇",
        "premium": "💎 Premium",
        "prices": "💰 Курсы криптовалют",
        "settings": "⚙️ Настройки",
        "profile": "👤 Профиль",
        "change_language": "🌐 Смена языка",
        "faq": "❓ FAQ",
        "suggestions": "💡 Предложения",
        "back": "🔙 Назад",
        "suggestion_text": (
            "💡 <b>Предложения</b>\n\nНапиши, что бы ты хотел добавить "
            "или улучшить в Bit Ref 4U.\n\nСообщение будет отправлено разработчику."
        ),
        "suggestion_sent": "✅ Спасибо! Твоё предложение отправлено разработчику.",
        "cancel": "❌ Отмена",
        "premium_active": "✅ Premium активен",
        "premium_inactive": "❌ Бесплатный аккаунт",
        "portfolio": "📁 Портфель",
        "alerts": "🔔 Алерты",
        "convert": "🔄 Конвертер",
        "top_movers": "🚀 Топ движения",
        "fng": "😨 Индекс страха",
        "translated_news": "🌍 Новости на языке",
        "premium_required": "🔒 Эта функция доступна только Premium-подписчикам.",
        "choose_language": "🌐 Выберите язык:\n\nChoose language:\n\nاختر اللغة:",
        # --- premium ---
        "premium_active_title": "💎 <b>Premium</b>",
        "premium_active_status": "✅ Подписка активна",
        "premium_active_until": "⏳ До: {end}",
        "premium_offer_title": "💎 <b>Bit Ref 4U Premium</b>",
        "premium_offer_features": (
            "🔒 Закрытый канал с новостями и дайджестом рынка\n"
            "📁 Трекер портфеля\n"
            "🔔 Ценовые алерты\n"
            "🔄 Конвертер валют\n"
            "🌍 Новости на твоём языке"
        ),
        "premium_offer_price": "💰 Цена: {price} USDT",
        "premium_offer_duration": "📅 Срок: {days} дней",
        "buy_button": "💳 Купить",
        # --- покупка / оплата ---
        "invoice_created_title": "💳 <b>Счёт создан!</b>",
        "invoice_created_amount": "💰 Сумма: {amount} USDT",
        "invoice_created_note": "После оплаты доступ будет открыт автоматически.",
        "pay_button": "💳 Оплатить",
        "invoice_error": "❌ Не удалось создать счёт. Попробуйте ещё раз чуть позже.",
        "payment_success_title": "🎉 <b>Оплата подтверждена!</b>",
        "payment_success_desc": "💎 Bit Ref 4U Premium активирован.\n🔒 Доступ к закрытому каналу:",
        "payment_success_duration": "⏳ Срок: {days} дней",
        "subscription_expired": (
            "⏳ <b>Premium закончился.</b>\n\n"
            "Чтобы продолжить пользоваться Bit Ref 4U Premium — продлите подписку."
        ),
        # --- курсы / рынок ---
        "prices_title": "💰 <b>Курсы криптовалют</b>",
        "prices_error": "❌ Не удалось получить курсы. Источники временно недоступны, попробуйте обновить через минуту.",
        "refresh_button": "🔄 Обновить",
        "top_gainers": "🚀 <b>Топ роста (24ч)</b>",
        "top_losers": "📉 <b>Топ падения (24ч)</b>",
        "top_movers_error": "❌ Не удалось получить данные о движении рынка.",
        "fng_title": "😨 <b>Индекс страха и жадности</b>",
        "fng_value": "Значение: <b>{value}/100</b>",
        "fng_status": "Статус: <b>{status}</b>",
        "fng_error": "❌ Индекс сейчас недоступен, попробуйте позже.",
        # --- профиль ---
        "profile_username": "👤 Username: {username}",
        "profile_id": "🆔 ID: <code>{id}</code>",
        "profile_status": "📌 Статус: {status}",
        "profile_end": "⏳ Действует до: {end}",
        "profile_status_premium": "💎 Premium",
        "profile_status_free": "🆓 Бесплатный",
        # --- портфель ---
        "portfolio_empty": "{title}\n\nПока пусто. Добавь первый актив 👇",
        "portfolio_total": "\n💼 Итого: <b>${total}</b>",
        "portfolio_add_button": "➕ Добавить актив",
        "portfolio_clear_button": "🗑 Очистить портфель",
        "portfolio_add_prompt": "➕ Отправь сообщение в формате:\n<code>BTC 0.5</code>\n\nДоступные монеты: {coins}",
        "portfolio_add_invalid": "❌ Неверный формат. Пример: <code>BTC 0.5</code>\nДоступно: {coins}",
        "portfolio_add_amount_invalid": "❌ Количество должно быть положительным числом.",
        "portfolio_added": "✅ Добавлено: {amount} {symbol}",
        # --- алерты ---
        "alerts_empty": "{title}\n\nАктивных алертов нет.",
        "alerts_add_button": "➕ Новый алерт",
        "alerts_clear_button": "🗑 Удалить все",
        "alerts_add_prompt": (
            "🔔 Отправь сообщение в формате:\n"
            "<code>BTC &gt; 70000</code> (уведомить, когда цена ВЫШЕ)\n"
            "<code>BTC &lt; 60000</code> (уведомить, когда цена НИЖЕ)"
        ),
        "alerts_add_invalid": "❌ Неверный формат. Пример: <code>BTC &gt; 70000</code>",
        "alerts_add_unknown_coin": "❌ Неизвестная монета. Доступно: {coins}",
        "alerts_add_price_invalid": "❌ Не удалось распознать цену.",
        "alerts_created": "🔔 Алерт создан: {symbol} {direction} ${price}",
        "alerts_direction_above": "выше",
        "alerts_direction_below": "ниже",
        "alerts_triggered": (
            "🔔 <b>Алерт сработал!</b>\n\n"
            "{symbol} сейчас ${price} ({direction} цели ${target})"
        ),
        # --- конвертер ---
        "convert_prompt": (
            "🔄 Отправь сообщение в формате:\n"
            "<code>0.5 BTC to ETH</code>\n"
            "<code>100 USD to BTC</code>\n"
            "<code>2 ETH to USD</code>"
        ),
        "convert_invalid": "❌ Неверный формат. Пример: <code>0.5 BTC to ETH</code>",
        "convert_amount_invalid": "❌ Не удалось распознать количество.",
        "convert_error": "❌ Не удалось выполнить конвертацию — проверь названия монет (доступно: {coins}, USD).",
        "convert_result": "🔄 {amount} {from_symbol} ≈ <b>{result} {to_symbol}</b>",
        # --- новости на языке ---
        "news_preparing": "Готовлю новости…",
        "news_translated_title": "🌍 <b>Bit Ref 4U — Новости</b>",
        "news_translated_empty": "❌ Новостей пока нет.",
    },
    "en": {
        "welcome": "🤖 <b>Bit Ref 4U</b>\n\nYour crypto assistant.\n\nChoose a section 👇",
        "premium": "💎 Premium",
        "prices": "💰 Crypto prices",
        "settings": "⚙️ Settings",
        "profile": "👤 Profile",
        "change_language": "🌐 Change language",
        "faq": "❓ FAQ",
        "suggestions": "💡 Suggestions",
        "back": "🔙 Back",
        "suggestion_text": (
            "💡 <b>Suggestions</b>\n\nWrite what you would like to add "
            "or improve in Bit Ref 4U.\n\nYour message will be sent to the developer."
        ),
        "suggestion_sent": "✅ Thanks! Your suggestion has been sent to the developer.",
        "cancel": "❌ Cancel",
        "premium_active": "✅ Premium active",
        "premium_inactive": "❌ Free account",
        "portfolio": "📁 Portfolio",
        "alerts": "🔔 Alerts",
        "convert": "🔄 Converter",
        "top_movers": "🚀 Top movers",
        "fng": "😨 Fear & Greed",
        "translated_news": "🌍 News in your language",
        "premium_required": "🔒 This feature is available to Premium subscribers only.",
        "choose_language": "🌐 Выберите язык:\n\nChoose language:\n\nاختر اللغة:",
        # --- premium ---
        "premium_active_title": "💎 <b>Premium</b>",
        "premium_active_status": "✅ Subscription active",
        "premium_active_until": "⏳ Until: {end}",
        "premium_offer_title": "💎 <b>Bit Ref 4U Premium</b>",
        "premium_offer_features": (
            "🔒 Private channel with news and market digest\n"
            "📁 Portfolio tracker\n"
            "🔔 Price alerts\n"
            "🔄 Currency converter\n"
            "🌍 News in your language"
        ),
        "premium_offer_price": "💰 Price: {price} USDT",
        "premium_offer_duration": "📅 Duration: {days} days",
        "buy_button": "💳 Buy",
        # --- purchase / payment ---
        "invoice_created_title": "💳 <b>Invoice created!</b>",
        "invoice_created_amount": "💰 Amount: {amount} USDT",
        "invoice_created_note": "Access will be granted automatically after payment.",
        "pay_button": "💳 Pay",
        "invoice_error": "❌ Couldn't create an invoice. Please try again shortly.",
        "payment_success_title": "🎉 <b>Payment confirmed!</b>",
        "payment_success_desc": "💎 Bit Ref 4U Premium activated.\n🔒 Access to the private channel:",
        "payment_success_duration": "⏳ Duration: {days} days",
        "subscription_expired": (
            "⏳ <b>Premium has expired.</b>\n\n"
            "To keep using Bit Ref 4U Premium — renew your subscription."
        ),
        # --- market ---
        "prices_title": "💰 <b>Crypto Prices</b>",
        "prices_error": "❌ Couldn't fetch prices. Sources are temporarily unavailable, please refresh in a minute.",
        "refresh_button": "🔄 Refresh",
        "top_gainers": "🚀 <b>Top gainers (24h)</b>",
        "top_losers": "📉 <b>Top losers (24h)</b>",
        "top_movers_error": "❌ Couldn't fetch market movers data.",
        "fng_title": "😨 <b>Fear & Greed Index</b>",
        "fng_value": "Value: <b>{value}/100</b>",
        "fng_status": "Status: <b>{status}</b>",
        "fng_error": "❌ Index is unavailable right now, try again later.",
        # --- profile ---
        "profile_username": "👤 Username: {username}",
        "profile_id": "🆔 ID: <code>{id}</code>",
        "profile_status": "📌 Status: {status}",
        "profile_end": "⏳ Valid until: {end}",
        "profile_status_premium": "💎 Premium",
        "profile_status_free": "🆓 Free",
        # --- portfolio ---
        "portfolio_empty": "{title}\n\nEmpty for now. Add your first asset 👇",
        "portfolio_total": "\n💼 Total: <b>${total}</b>",
        "portfolio_add_button": "➕ Add asset",
        "portfolio_clear_button": "🗑 Clear portfolio",
        "portfolio_add_prompt": "➕ Send a message in the format:\n<code>BTC 0.5</code>\n\nAvailable coins: {coins}",
        "portfolio_add_invalid": "❌ Invalid format. Example: <code>BTC 0.5</code>\nAvailable: {coins}",
        "portfolio_add_amount_invalid": "❌ Amount must be a positive number.",
        "portfolio_added": "✅ Added: {amount} {symbol}",
        # --- alerts ---
        "alerts_empty": "{title}\n\nNo active alerts.",
        "alerts_add_button": "➕ New alert",
        "alerts_clear_button": "🗑 Clear all",
        "alerts_add_prompt": (
            "🔔 Send a message in the format:\n"
            "<code>BTC &gt; 70000</code> (notify when price is ABOVE)\n"
            "<code>BTC &lt; 60000</code> (notify when price is BELOW)"
        ),
        "alerts_add_invalid": "❌ Invalid format. Example: <code>BTC &gt; 70000</code>",
        "alerts_add_unknown_coin": "❌ Unknown coin. Available: {coins}",
        "alerts_add_price_invalid": "❌ Couldn't parse the price.",
        "alerts_created": "🔔 Alert created: {symbol} {direction} ${price}",
        "alerts_direction_above": "above",
        "alerts_direction_below": "below",
        "alerts_triggered": (
            "🔔 <b>Alert triggered!</b>\n\n"
            "{symbol} is now ${price} ({direction} target ${target})"
        ),
        # --- converter ---
        "convert_prompt": (
            "🔄 Send a message in the format:\n"
            "<code>0.5 BTC to ETH</code>\n"
            "<code>100 USD to BTC</code>\n"
            "<code>2 ETH to USD</code>"
        ),
        "convert_invalid": "❌ Invalid format. Example: <code>0.5 BTC to ETH</code>",
        "convert_amount_invalid": "❌ Couldn't parse the amount.",
        "convert_error": "❌ Couldn't convert — check the coin names (available: {coins}, USD).",
        "convert_result": "🔄 {amount} {from_symbol} ≈ <b>{result} {to_symbol}</b>",
        # --- translated news ---
        "news_preparing": "Preparing the news…",
        "news_translated_title": "🌍 <b>Bit Ref 4U — News</b>",
        "news_translated_empty": "❌ No news right now.",
    },
    "ar": {
        "welcome": "🤖 <b>Bit Ref 4U</b>\n\nمساعد العملات الرقمية الخاص بك.\n\nاختر القسم 👇",
        "premium": "💎 Premium",
        "prices": "💰 أسعار العملات الرقمية",
        "settings": "⚙️ الإعدادات",
        "profile": "👤 الملف الشخصي",
        "change_language": "🌐 تغيير اللغة",
        "faq": "❓ الأسئلة الشائعة",
        "suggestions": "💡 الاقتراحات",
        "back": "🔙 رجوع",
        "suggestion_text": (
            "💡 <b>الاقتراحات</b>\n\nاكتب ما تريد إضافته أو تحسينه "
            "في Bit Ref 4U.\n\nسيتم إرسال رسالتك إلى المطور."
        ),
        "suggestion_sent": "✅ شكراً! تم إرسال اقتراحك إلى المطور.",
        "cancel": "❌ إلغاء",
        "premium_active": "✅ Premium فعال",
        "premium_inactive": "❌ حساب مجاني",
        "portfolio": "📁 المحفظة",
        "alerts": "🔔 التنبيهات",
        "convert": "🔄 المحول",
        "top_movers": "🚀 الأكثر حركة",
        "fng": "😨 مؤشر الخوف والجشع",
        "translated_news": "🌍 الأخبار بلغتك",
        "premium_required": "🔒 هذه الميزة متاحة فقط لمشتركي Premium.",
        "choose_language": "🌐 Выберите язык:\n\nChoose language:\n\nاختر اللغة:",
        # --- premium ---
        "premium_active_title": "💎 <b>Premium</b>",
        "premium_active_status": "✅ الاشتراك فعال",
        "premium_active_until": "⏳ حتى: {end}",
        "premium_offer_title": "💎 <b>Bit Ref 4U Premium</b>",
        "premium_offer_features": (
            "🔒 قناة خاصة بالأخبار ودايجست السوق\n"
            "📁 متتبع المحفظة\n"
            "🔔 تنبيهات الأسعار\n"
            "🔄 محول العملات\n"
            "🌍 الأخبار بلغتك"
        ),
        "premium_offer_price": "💰 السعر: {price} USDT",
        "premium_offer_duration": "📅 المدة: {days} يوماً",
        "buy_button": "💳 شراء",
        # --- الدفع ---
        "invoice_created_title": "💳 <b>تم إنشاء الفاتورة!</b>",
        "invoice_created_amount": "💰 المبلغ: {amount} USDT",
        "invoice_created_note": "سيتم منح الوصول تلقائياً بعد الدفع.",
        "pay_button": "💳 دفع",
        "invoice_error": "❌ تعذر إنشاء الفاتورة. حاول مرة أخرى بعد قليل.",
        "payment_success_title": "🎉 <b>تم تأكيد الدفع!</b>",
        "payment_success_desc": "💎 تم تفعيل Bit Ref 4U Premium.\n🔒 الوصول إلى القناة الخاصة:",
        "payment_success_duration": "⏳ المدة: {days} يوماً",
        "subscription_expired": (
            "⏳ <b>انتهى اشتراك Premium.</b>\n\n"
            "لمواصلة استخدام Bit Ref 4U Premium — جدد اشتراكك."
        ),
        # --- السوق ---
        "prices_title": "💰 <b>أسعار العملات الرقمية</b>",
        "prices_error": "❌ تعذر جلب الأسعار. المصادر غير متاحة مؤقتاً، حاول التحديث بعد دقيقة.",
        "refresh_button": "🔄 تحديث",
        "top_gainers": "🚀 <b>الأكثر ارتفاعاً (24س)</b>",
        "top_losers": "📉 <b>الأكثر انخفاضاً (24س)</b>",
        "top_movers_error": "❌ تعذر جلب بيانات حركة السوق.",
        "fng_title": "😨 <b>مؤشر الخوف والجشع</b>",
        "fng_value": "القيمة: <b>{value}/100</b>",
        "fng_status": "الحالة: <b>{status}</b>",
        "fng_error": "❌ المؤشر غير متاح حالياً، حاول لاحقاً.",
        # --- الملف الشخصي ---
        "profile_username": "👤 اسم المستخدم: {username}",
        "profile_id": "🆔 المعرف: <code>{id}</code>",
        "profile_status": "📌 الحالة: {status}",
        "profile_end": "⏳ صالح حتى: {end}",
        "profile_status_premium": "💎 Premium",
        "profile_status_free": "🆓 مجاني",
        # --- المحفظة ---
        "portfolio_empty": "{title}\n\nفارغة الآن. أضف أول أصل 👇",
        "portfolio_total": "\n💼 الإجمالي: <b>${total}</b>",
        "portfolio_add_button": "➕ إضافة أصل",
        "portfolio_clear_button": "🗑 مسح المحفظة",
        "portfolio_add_prompt": "➕ أرسل رسالة بالصيغة:\n<code>BTC 0.5</code>\n\nالعملات المتاحة: {coins}",
        "portfolio_add_invalid": "❌ صيغة غير صحيحة. مثال: <code>BTC 0.5</code>\nالمتاح: {coins}",
        "portfolio_add_amount_invalid": "❌ يجب أن تكون الكمية رقماً موجباً.",
        "portfolio_added": "✅ تمت الإضافة: {amount} {symbol}",
        # --- التنبيهات ---
        "alerts_empty": "{title}\n\nلا توجد تنبيهات نشطة.",
        "alerts_add_button": "➕ تنبيه جديد",
        "alerts_clear_button": "🗑 حذف الكل",
        "alerts_add_prompt": (
            "🔔 أرسل رسالة بالصيغة:\n"
            "<code>BTC &gt; 70000</code> (تنبيه عند الارتفاع فوق السعر)\n"
            "<code>BTC &lt; 60000</code> (تنبيه عند الانخفاض دون السعر)"
        ),
        "alerts_add_invalid": "❌ صيغة غير صحيحة. مثال: <code>BTC &gt; 70000</code>",
        "alerts_add_unknown_coin": "❌ عملة غير معروفة. المتاح: {coins}",
        "alerts_add_price_invalid": "❌ تعذر التعرف على السعر.",
        "alerts_created": "🔔 تم إنشاء التنبيه: {symbol} {direction} ${price}",
        "alerts_direction_above": "أعلى من",
        "alerts_direction_below": "أدنى من",
        "alerts_triggered": (
            "🔔 <b>تم تفعيل التنبيه!</b>\n\n"
            "{symbol} الآن ${price} ({direction} الهدف ${target})"
        ),
        # --- المحول ---
        "convert_prompt": (
            "🔄 أرسل رسالة بالصيغة:\n"
            "<code>0.5 BTC to ETH</code>\n"
            "<code>100 USD to BTC</code>\n"
            "<code>2 ETH to USD</code>"
        ),
        "convert_invalid": "❌ صيغة غير صحيحة. مثال: <code>0.5 BTC to ETH</code>",
        "convert_amount_invalid": "❌ تعذر التعرف على الكمية.",
        "convert_error": "❌ تعذر التحويل — تحقق من أسماء العملات (المتاح: {coins}, USD).",
        "convert_result": "🔄 {amount} {from_symbol} ≈ <b>{result} {to_symbol}</b>",
        # --- الأخبار بلغتك ---
        "news_preparing": "جارٍ تحضير الأخبار…",
        "news_translated_title": "🌍 <b>Bit Ref 4U — الأخبار</b>",
        "news_translated_empty": "❌ لا توجد أخبار حالياً.",
    },
}


def get_text(language: str, key: str, **kwargs) -> str:
    if language not in TEXTS:
        language = "ru"
    template = TEXTS[language].get(key, TEXTS["ru"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


# =========================================================================
# TELEGRAM UI — МЕНЮ
# =========================================================================

CHOOSE_LANGUAGE_TEXT = "🌐 Выберите язык:\n\nChoose language:\n\nاختر اللغة:"


def language_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇦🇪 العربية", callback_data="lang_ar")],
        ]
    )


def main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💎 Premium", callback_data="premium")],
            [InlineKeyboardButton(get_text(lang, "prices"), callback_data="prices")],
            [InlineKeyboardButton(get_text(lang, "top_movers"), callback_data="top_movers")],
            [InlineKeyboardButton(get_text(lang, "fng"), callback_data="fng")],
            [InlineKeyboardButton(get_text(lang, "settings"), callback_data="settings")],
            [InlineKeyboardButton(get_text(lang, "profile"), callback_data="profile")],
        ]
    )


def back_button(target: str = "back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Назад", callback_data=target)]]
    )


# =========================================================================
# TELEGRAM UI — ОСНОВНЫЕ ХЕНДЛЕРЫ
# =========================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user(user.id, user.username)

    language = await get_language(user.id)
    if not language:
        # ФИКС: у новых пользователей language теперь NULL, а не 'ru' по
        # умолчанию (раньше DEFAULT 'ru' в схеме означал, что этот экран
        # никогда не показывался). Показываем выбор языка один раз при
        # первом запуске, до входа в главное меню.
        await update.message.reply_text(
            CHOOSE_LANGUAGE_TEXT,
            reply_markup=language_menu(),
        )
        return

    await update.message.reply_text(
        get_text(language, "welcome"),
        parse_mode="HTML",
        reply_markup=main_menu(language),
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.split("_")[1]
    await update_language(query.from_user.id, lang)

    await query.edit_message_text(
        get_text(lang, "welcome"),
        parse_mode="HTML",
        reply_markup=main_menu(lang),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    await query.edit_message_text(
        get_text(lang, "settings"),
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(get_text(lang, "change_language"), callback_data="change_language")],
                [InlineKeyboardButton(get_text(lang, "faq"), callback_data="faq")],
                [InlineKeyboardButton(get_text(lang, "suggestions"), callback_data="suggestions")],
                [InlineKeyboardButton(get_text(lang, "back"), callback_data="back")],
            ]
        ),
    )


async def change_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        CHOOSE_LANGUAGE_TEXT,
        reply_markup=language_menu(),
    )


FAQ_TEXTS = {
    "ru": (
        "❓ <b>FAQ</b>\n\n"
        "💎 Premium открывает доступ к закрытому каналу, портфелю, "
        "алертам, конвертеру и дайджестам рынка.\n\n"
        "📅 Подписка действует {days} дней.\n\n"
        "💰 Оплата производится в USDT."
    ),
    "en": (
        "❓ <b>FAQ</b>\n\n"
        "💎 Premium unlocks the private channel, portfolio tracker, "
        "price alerts, converter and market digests.\n\n"
        "📅 Subscription lasts {days} days.\n\n"
        "💰 Payment is made in USDT."
    ),
    "ar": (
        "❓ <b>الأسئلة الشائعة</b>\n\n"
        "💎 يمنحك Premium الوصول إلى القناة الخاصة والمحفظة والتنبيهات "
        "والمحول ودايجست السوق.\n\n"
        "📅 الاشتراك لمدة {days} يوماً.\n\n"
        "💰 الدفع يتم بواسطة USDT."
    ),
}


async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    text = FAQ_TEXTS.get(lang, FAQ_TEXTS["ru"]).format(days=SUBSCRIPTION_DAYS)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=back_button("settings"),
    )


async def suggestions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    context.user_data["state"] = "waiting_suggestion"

    await query.edit_message_text(
        get_text(lang, "suggestion_text"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(get_text(lang, "cancel"), callback_data="cancel_state")]]
        ),
    )


async def cancel_state_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = None

    lang = await get_language(query.from_user.id) or "ru"
    await query.edit_message_text(
        get_text(lang, "welcome"),
        parse_mode="HTML",
        reply_markup=main_menu(lang),
    )


# --- PREMIUM / ПОКУПКА -------------------------------------------------------

async def premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    user = await get_user(query.from_user.id)
    active = is_premium_active(user)

    if active:
        end_display = user["subscription_end"][:19].replace("T", " ")
        text = (
            f"{get_text(lang, 'premium_active_title')}\n\n"
            f"{get_text(lang, 'premium_active_status')}\n\n"
            f"{get_text(lang, 'premium_active_until', end=end_display)}"
        )
        keyboard = [
            [InlineKeyboardButton(get_text(lang, "portfolio"), callback_data="portfolio")],
            [InlineKeyboardButton(get_text(lang, "alerts"), callback_data="alerts")],
            [InlineKeyboardButton(get_text(lang, "convert"), callback_data="convert")],
            [InlineKeyboardButton(get_text(lang, "translated_news"), callback_data="news_translated")],
            [InlineKeyboardButton(get_text(lang, "back"), callback_data="back")],
        ]
    else:
        text = (
            f"{get_text(lang, 'premium_offer_title')}\n\n"
            f"{get_text(lang, 'premium_offer_features')}\n\n"
            f"{get_text(lang, 'premium_offer_price', price=PRICE_USDT)}\n"
            f"{get_text(lang, 'premium_offer_duration', days=SUBSCRIPTION_DAYS)}"
        )
        keyboard = [
            [InlineKeyboardButton(get_text(lang, "buy_button"), callback_data="buy")],
            [InlineKeyboardButton(get_text(lang, "back"), callback_data="back")],
        ]

    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    try:
        invoice = await create_invoice(user_id=query.from_user.id, amount=PRICE_USDT)
        await add_invoice(invoice["invoice_id"], query.from_user.id, PRICE_USDT, "USDT")

        text = (
            f"{get_text(lang, 'invoice_created_title')}\n\n"
            f"{get_text(lang, 'invoice_created_amount', amount=PRICE_USDT)}\n\n"
            f"{get_text(lang, 'invoice_created_note')}"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(get_text(lang, "pay_button"), url=invoice["pay_url"])],
                    [InlineKeyboardButton(get_text(lang, "back"), callback_data="premium")],
                ]
            ),
        )
    except Exception as e:
        log.error("Invoice creation failed: %s", e)
        await query.edit_message_text(
            get_text(lang, "invoice_error"),
            reply_markup=back_button("premium"),
        )


# --- КУРСЫ / ТОП ДВИЖЕНИЯ / FEAR&GREED ---------------------------------------

async def prices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    try:
        market = await get_full_market()
        lines = [f"{get_text(lang, 'prices_title')}\n"]
        for symbol, info in SUPPORTED_COINS.items():
            coin = market.get(symbol)
            if not coin:
                continue
            arrow = "🟢" if coin["change_24h"] >= 0 else "🔴"
            lines.append(
                f"{arrow} {info['name']} ({symbol}): <b>${format_price(coin['price'])}</b> "
                f"({coin['change_24h']:+.2f}%)"
            )
        text = "\n".join(lines)
    except Exception as e:
        log.error("prices_callback failed: %s", e)
        text = get_text(lang, "prices_error")

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(get_text(lang, "refresh_button"), callback_data="prices")],
                [InlineKeyboardButton(get_text(lang, "back"), callback_data="back")],
            ]
        ),
    )


async def top_movers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    try:
        gainers, losers = await get_top_movers(5)
        lines = [get_text(lang, "top_gainers")]
        for symbol, data in gainers:
            lines.append(f"🟢 {symbol}: {data['change_24h']:+.2f}%  (${format_price(data['price'])})")
        lines.append(f"\n{get_text(lang, 'top_losers')}")
        for symbol, data in losers:
            lines.append(f"🔴 {symbol}: {data['change_24h']:+.2f}%  (${format_price(data['price'])})")
        text = "\n".join(lines)
    except Exception as e:
        log.error("top_movers_callback failed: %s", e)
        text = get_text(lang, "top_movers_error")

    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=back_button()
    )


async def fng_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    fng = await get_fear_greed()
    if fng:
        bar_filled = round(fng["value"] / 10)
        bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)
        text = (
            f"{get_text(lang, 'fng_title')}\n\n"
            f"{bar}\n\n"
            f"{get_text(lang, 'fng_value', value=fng['value'])}\n"
            f"{get_text(lang, 'fng_status', status=fng['classification'])}"
        )
    else:
        text = get_text(lang, "fng_error")

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_button())


# --- PROFILE ------------------------------------------------------------------

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"

    user = await get_user(query.from_user.id)
    username = f"@{query.from_user.username}" if query.from_user.username else "None"

    # ФИКС: раньше status/end читались из user[3] (subscription_status),
    # что при статусе 'inactive' (непустая строка -> truthy) показывало
    # "Premium" даже неактивным пользователям.
    if is_premium_active(user):
        status = get_text(lang, "profile_status_premium")
        end = user["subscription_end"][:19].replace("T", " ")
    else:
        status = get_text(lang, "profile_status_free")
        end = "-"

    text = (
        f"{get_text(lang, 'profile')}\n\n"
        f"{get_text(lang, 'profile_username', username=username)}\n"
        f"{get_text(lang, 'profile_id', id=query.from_user.id)}\n\n"
        f"{get_text(lang, 'profile_status', status=status)}\n"
        f"{get_text(lang, 'profile_end', end=end)}"
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_button())


# --- ПОРТФЕЛЬ (новое, premium) -----------------------------------------------

async def _portfolio_text_and_keyboard(user_id: int, lang: str):
    holdings = await get_portfolio(user_id)
    if not holdings:
        text = get_text(lang, "portfolio_empty", title=get_text(lang, "portfolio"))
    else:
        try:
            market = await get_full_market()
        except Exception:
            market = {}

        lines = [f"{get_text(lang, 'portfolio')}\n"]
        total = 0.0
        for h in holdings:
            price = market.get(h["symbol"], {}).get("price", 0)
            value = price * h["amount"]
            total += value
            lines.append(f"• {h['amount']:g} {h['symbol']} ≈ ${value:,.2f}")
        lines.append(get_text(lang, "portfolio_total", total=f"{total:,.2f}"))
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(get_text(lang, "portfolio_add_button"), callback_data="portfolio_add")],
            [InlineKeyboardButton(get_text(lang, "portfolio_clear_button"), callback_data="portfolio_clear")],
            [InlineKeyboardButton(get_text(lang, "back"), callback_data="premium")],
        ]
    )
    return text, keyboard


async def portfolio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"
    user = await get_user(query.from_user.id)

    if not is_premium_active(user):
        await query.edit_message_text(get_text(lang, "premium_required"), reply_markup=back_button("premium"))
        return

    text, keyboard = await _portfolio_text_and_keyboard(query.from_user.id, lang)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def portfolio_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"
    context.user_data["state"] = "waiting_portfolio_add"

    coins = ", ".join(SUPPORTED_COINS.keys())
    await query.edit_message_text(
        get_text(lang, "portfolio_add_prompt", coins=coins),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(get_text(lang, "cancel"), callback_data="cancel_state")]]
        ),
    )


async def portfolio_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await clear_portfolio(query.from_user.id)

    lang = await get_language(query.from_user.id) or "ru"
    text, keyboard = await _portfolio_text_and_keyboard(query.from_user.id, lang)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


# --- АЛЕРТЫ (новое, premium) --------------------------------------------------

async def _alerts_text_and_keyboard(user_id: int, lang: str):
    alerts = await get_user_alerts(user_id)
    if not alerts:
        text = get_text(lang, "alerts_empty", title=get_text(lang, "alerts"))
    else:
        lines = [f"{get_text(lang, 'alerts')}\n"]
        arrow = {
            "above": get_text(lang, "alerts_direction_above"),
            "below": get_text(lang, "alerts_direction_below"),
        }
        for a in alerts:
            lines.append(f"• {a['symbol']} {arrow[a['direction']]} ${format_price(a['target_price'])}")
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(get_text(lang, "alerts_add_button"), callback_data="alerts_add")],
            [InlineKeyboardButton(get_text(lang, "alerts_clear_button"), callback_data="alerts_clear")],
            [InlineKeyboardButton(get_text(lang, "back"), callback_data="premium")],
        ]
    )
    return text, keyboard


async def alerts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"
    user = await get_user(query.from_user.id)

    if not is_premium_active(user):
        await query.edit_message_text(get_text(lang, "premium_required"), reply_markup=back_button("premium"))
        return

    text, keyboard = await _alerts_text_and_keyboard(query.from_user.id, lang)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def alerts_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"
    context.user_data["state"] = "waiting_alert_add"

    await query.edit_message_text(
        get_text(lang, "alerts_add_prompt"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(get_text(lang, "cancel"), callback_data="cancel_state")]]
        ),
    )


async def alerts_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await clear_alerts(query.from_user.id)

    lang = await get_language(query.from_user.id) or "ru"
    text, keyboard = await _alerts_text_and_keyboard(query.from_user.id, lang)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


# --- КОНВЕРТЕР (новое, premium) ----------------------------------------------

async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_language(query.from_user.id) or "ru"
    user = await get_user(query.from_user.id)

    if not is_premium_active(user):
        await query.edit_message_text(get_text(lang, "premium_required"), reply_markup=back_button("premium"))
        return

    context.user_data["state"] = "waiting_convert"
    await query.edit_message_text(
        get_text(lang, "convert_prompt"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(get_text(lang, "cancel"), callback_data="cancel_state")]]
        ),
    )


# --- НОВОСТИ НА ЯЗЫКЕ ПОЛЬЗОВАТЕЛЯ (новое, premium) ---------------------------

async def news_translated_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await get_language(query.from_user.id) or "ru"
    await query.answer(get_text(lang, "news_preparing"))
    user = await get_user(query.from_user.id)

    if not is_premium_active(user):
        await query.edit_message_text(get_text(lang, "premium_required"), reply_markup=back_button("premium"))
        return

    news_list = get_latest_news(per_source=2)[:3]
    if not news_list:
        await query.edit_message_text(get_text(lang, "news_translated_empty"), reply_markup=back_button("premium"))
        return

    blocks = []
    for news in news_list:
        title = await translate_text(news.get("title", ""), lang)
        summary = await translate_text(summarize(news), lang)
        blocks.append(f"📰 <b>{escape_html(title)}</b>\n<i>{escape_html(summary)}</i>")

    text = f"{get_text(lang, 'news_translated_title')}\n\n" + "\n\n".join(blocks)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_button("premium"))


# --- ТЕКСТОВЫЙ ВВОД (предложения / портфель / алерты / конвертер) ------------

async def receive_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await save_suggestion(user.id, user.username, update.message.text)

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "💡 <b>Новое предложение</b>\n\n"
            f"👤 @{user.username}\n"
            f"🆔 {user.id}\n\n"
            f"💬 {update.message.text}"
        ),
        parse_mode="HTML",
    )

    lang = await get_language(user.id) or "ru"
    await update.message.reply_text(get_text(lang, "suggestion_sent"), reply_markup=main_menu(lang))


async def receive_portfolio_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().upper().split()
    lang = await get_language(update.effective_user.id) or "ru"
    coins = ", ".join(SUPPORTED_COINS.keys())

    if len(parts) != 2 or parts[0] not in SUPPORTED_COINS:
        await update.message.reply_text(
            get_text(lang, "portfolio_add_invalid", coins=coins),
            parse_mode="HTML",
        )
        return

    try:
        amount = float(parts[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(get_text(lang, "portfolio_add_amount_invalid"))
        return

    await add_holding(update.effective_user.id, parts[0], amount)
    context.user_data["state"] = None

    await update.message.reply_text(
        get_text(lang, "portfolio_added", amount=f"{amount:g}", symbol=parts[0]),
        reply_markup=main_menu(lang),
    )


ALERT_RE = re.compile(r"^([A-Za-z]{2,10})\s*([<>])\s*([\d.,]+)$")


async def receive_alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_language(update.effective_user.id) or "ru"
    match = ALERT_RE.match(update.message.text.strip())

    if not match:
        await update.message.reply_text(
            get_text(lang, "alerts_add_invalid"),
            parse_mode="HTML",
        )
        return

    symbol, sign, price_str = match.groups()
    symbol = symbol.upper()
    if symbol not in SUPPORTED_COINS:
        coins = ", ".join(SUPPORTED_COINS.keys())
        await update.message.reply_text(get_text(lang, "alerts_add_unknown_coin", coins=coins))
        return

    try:
        target_price = float(price_str.replace(",", "."))
    except ValueError:
        await update.message.reply_text(get_text(lang, "alerts_add_price_invalid"))
        return

    direction = "above" if sign == ">" else "below"
    await add_alert(update.effective_user.id, symbol, target_price, direction)
    context.user_data["state"] = None

    direction_text = get_text(
        lang, "alerts_direction_above" if direction == "above" else "alerts_direction_below"
    )
    await update.message.reply_text(
        get_text(
            lang, "alerts_created", symbol=symbol, direction=direction_text,
            price=format_price(target_price),
        ),
        reply_markup=main_menu(lang),
    )


CONVERT_RE = re.compile(r"^([\d.,]+)\s*([A-Za-z]{2,10})\s+(?:to|в|->)\s+([A-Za-z]{2,10})$", re.IGNORECASE)


async def receive_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_language(update.effective_user.id) or "ru"
    match = CONVERT_RE.match(update.message.text.strip())

    if not match:
        await update.message.reply_text(
            get_text(lang, "convert_invalid"),
            parse_mode="HTML",
        )
        return

    amount_str, from_symbol, to_symbol = match.groups()
    try:
        amount = float(amount_str.replace(",", "."))
    except ValueError:
        await update.message.reply_text(get_text(lang, "convert_amount_invalid"))
        return

    result = await convert_amount(amount, from_symbol, to_symbol)
    context.user_data["state"] = None

    if result is None:
        coins = ", ".join(SUPPORTED_COINS.keys())
        await update.message.reply_text(
            get_text(lang, "convert_error", coins=coins),
            reply_markup=main_menu(lang),
        )
        return

    await update.message.reply_text(
        get_text(
            lang, "convert_result",
            amount=f"{amount:g}", from_symbol=from_symbol.upper(),
            result=f"{result:,.6f}", to_symbol=to_symbol.upper(),
        ),
        parse_mode="HTML",
        reply_markup=main_menu(lang),
    )


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единый роутер свободного текстового ввода: направляет сообщение в
    нужный обработчик в зависимости от того, чего мы ждём от пользователя."""
    state = context.user_data.get("state")

    handlers = {
        "waiting_suggestion": receive_suggestion,
        "waiting_portfolio_add": receive_portfolio_add,
        "waiting_alert_add": receive_alert_add,
        "waiting_convert": receive_convert,
    }

    handler = handlers.get(state)
    if handler:
        await handler(update, context)


# --- CALLBACK ROUTER -----------------------------------------------------------

CALLBACK_HANDLERS = {
    "premium": premium_callback,
    "buy": buy_callback,
    "prices": prices_callback,
    "top_movers": top_movers_callback,
    "fng": fng_callback,
    "profile": profile_callback,
    "settings": settings_callback,
    "change_language": change_language_callback,
    "faq": faq_callback,
    "suggestions": suggestions_callback,
    "cancel_state": cancel_state_callback,
    "portfolio": portfolio_callback,
    "portfolio_add": portfolio_add_callback,
    "portfolio_clear": portfolio_clear_callback,
    "alerts": alerts_callback,
    "alerts_add": alerts_add_callback,
    "alerts_clear": alerts_clear_callback,
    "convert": convert_callback,
    "news_translated": news_translated_callback,
}


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("lang_"):
        await language_callback(update, context)
        return

    if data == "back":
        await query.answer()
        lang = await get_language(query.from_user.id) or "ru"
        await query.edit_message_text(
            get_text(lang, "welcome"),
            parse_mode="HTML",
            reply_markup=main_menu(lang),
        )
        return

    handler = CALLBACK_HANDLERS.get(data)
    if handler:
        await handler(update, context)
    else:
        await query.answer()


async def admin_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("✅ Admin доступ работает")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Unhandled error: %s", context.error, exc_info=context.error)


# =========================================================================
# ФОНОВЫЕ ЗАДАЧИ  (было checker.py + content_manager.py, + новое: alerts,
# рыночный дайджест)
# =========================================================================

async def give_channel_access(app: Application, user_id: int) -> bool:
    try:
        lang = await get_language(user_id) or "ru"
        invite_link = await app.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID, member_limit=1
        )
        text = (
            f"{get_text(lang, 'payment_success_title')}\n\n"
            f"{get_text(lang, 'payment_success_desc')}\n\n"
            f"{invite_link.invite_link}\n\n"
            f"{get_text(lang, 'payment_success_duration', days=SUBSCRIPTION_DAYS)}"
        )
        await app.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        return True
    except Exception as e:
        log.error("Invite error for user %s: %s", user_id, e)
        return False


async def check_payments(app: Application):
    invoices = await get_active_invoices()

    for invoice in invoices:
        invoice_id = invoice["invoice_id"]
        user_id = invoice["user_id"]

        try:
            if not await is_invoice_paid(invoice_id):
                continue

            await mark_paid(invoice_id)

            # ФИКС: activate_subscription теперь вызывается с правильной
            # сигнатурой (user_id, days) вместо несуществующей
            # (user_id, now_iso, end_iso), которая раньше валила весь блок
            # с TypeError и обрывала отправку приглашения ниже.
            await activate_subscription(user_id, SUBSCRIPTION_DAYS)

            # ФИКС: аргументы переданы в правильном порядке
            # (invoice_id, user_id, amount, currency).
            await save_payment(invoice_id, user_id, invoice["amount"], invoice["currency"] or "USDT")

            if not await invite_sent(invoice_id):
                sent = await give_channel_access(app, user_id)
                if sent:
                    await mark_invite_sent(invoice_id)

        except Exception as e:
            log.error("Payment check error for invoice %s: %s", invoice_id, e)


async def remove_expired_users(app: Application):
    expired = await get_expired_subscriptions()

    for user_id in expired:
        try:
            lang = await get_language(user_id) or "ru"
            await deactivate_subscription(user_id)
            await app.bot.send_message(
                chat_id=user_id,
                text=get_text(lang, "subscription_expired"),
                parse_mode="HTML",
            )
        except Exception as e:
            log.error("Expire error for user %s: %s", user_id, e)


async def payment_checker(app: Application):
    log.info("Payment checker started")
    while True:
        try:
            await check_payments(app)
            await remove_expired_users(app)
        except Exception as e:
            log.error("Checker loop error: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)


async def content_manager(app: Application):
    log.info("Content manager started")
    while True:
        try:
            news_list = get_latest_news()
            for news in news_list:
                if await is_news_published(news["link"], "private"):
                    continue

                text = generate_private_post(news)
                photo = get_random_image()

                try:
                    await app.bot.send_photo(
                        chat_id=PRIVATE_CHANNEL_ID,
                        photo=photo,
                        caption=text,
                        parse_mode="HTML",
                    )
                except Exception as photo_error:
                    # file_id может быть невалиден для нового токена бота —
                    # не теряем новость, публикуем текстом.
                    log.warning("Photo send failed, falling back to text: %s", photo_error)
                    await app.bot.send_message(
                        chat_id=PRIVATE_CHANNEL_ID, text=text, parse_mode="HTML"
                    )

                await save_published_news(news["link"], "private")
                log.info("Private post sent: %s", news["title"])
                break

        except Exception as e:
            log.error("Content manager error: %s", e)

        await asyncio.sleep(PRIVATE_POST_INTERVAL)


async def market_digest_task(app: Application):
    """Новое: периодический аналитический дайджест в приватный канал."""
    log.info("Market digest task started")
    while True:
        await asyncio.sleep(MARKET_DIGEST_INTERVAL)
        try:
            digest = await generate_market_digest()
            if digest:
                await app.bot.send_message(
                    chat_id=PRIVATE_CHANNEL_ID, text=digest, parse_mode="HTML"
                )
                log.info("Market digest posted")
        except Exception as e:
            log.error("Market digest error: %s", e)


async def alert_checker_task(app: Application):
    """Новое: проверка ценовых алертов пользователей."""
    log.info("Alert checker started")
    while True:
        try:
            alerts = await get_active_alerts()
            if alerts:
                market = await get_full_market()
                for alert in alerts:
                    coin = market.get(alert["symbol"])
                    if not coin:
                        continue

                    price = coin["price"]
                    triggered = (
                        alert["direction"] == "above" and price >= alert["target_price"]
                    ) or (
                        alert["direction"] == "below" and price <= alert["target_price"]
                    )

                    if triggered:
                        try:
                            lang = await get_language(alert["user_id"]) or "ru"
                            direction_text = get_text(
                                lang,
                                "alerts_direction_above" if alert["direction"] == "above" else "alerts_direction_below",
                            )
                            text = get_text(
                                lang, "alerts_triggered",
                                symbol=alert["symbol"], price=format_price(price),
                                direction=direction_text, target=format_price(alert["target_price"]),
                            )
                            await app.bot.send_message(
                                chat_id=alert["user_id"], text=text, parse_mode="HTML"
                            )
                        finally:
                            await deactivate_alert(alert["id"])

        except Exception as e:
            log.error("Alert checker error: %s", e)

        await asyncio.sleep(ALERT_CHECK_INTERVAL)


# =========================================================================
# WEB (keep-alive)  (было web.py)
# =========================================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Bit Ref 4U Bot is running!"


def run_web():
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


# =========================================================================
# ЗАПУСК
# =========================================================================

async def post_init(application: Application):
    await init_db()
    asyncio.create_task(payment_checker(application))
    asyncio.create_task(content_manager(application))
    asyncio.create_task(market_digest_task(application))
    asyncio.create_task(alert_checker_task(application))


def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_test))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
    )

    threading.Thread(target=run_web, daemon=True).start()

    log.info("Bit Ref 4U started (PID %s)", os.getpid())
    application.run_polling()


if __name__ == "__main__":
    main()
