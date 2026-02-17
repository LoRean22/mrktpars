import asyncio
from datetime import datetime, timedelta
import pymysql

from core.database import get_pool

from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


active_monitors = {}


def get_next_proxy():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proxies
                WHERE (is_banned=0 OR banned_until < NOW() OR banned_until IS NULL)
                ORDER BY last_used_at IS NULL DESC, last_used_at ASC
                LIMIT 1
            """)
            proxy = cursor.fetchone()

            if not proxy:
                return None

            cursor.execute("""
                UPDATE proxies
                SET last_used_at=%s
                WHERE id=%s
            """, (datetime.now(), proxy["id"]))

            connection.commit()
            return proxy

    finally:
        connection.close()


def mark_proxy_banned(proxy_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE proxies
                SET is_banned=1,
                    banned_until=%s
                WHERE id=%s
            """, (datetime.now() + timedelta(minutes=10), proxy_id))
            connection.commit()

    finally:
        connection.close()


def format_message(item):
    return (
        f"📦 {item.title}\n"
        f"💰 {item.price} ₽\n"
        f"🔗 {item.url}\n"
    )


async def monitor_worker(tg_id: int, search_url: str):

    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:

            # --- прогрев ---
            proxy_row = get_next_proxy()
            if not proxy_row:
                return

            parser = AvitoParser(proxy=proxy_row["proxy"])
            items, status = await parser.parse_once(search_url)

            for item in items:
                await cursor.execute("""
                    INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                    VALUES (%s, %s, NOW())
                """, (tg_id, item.id))

    # --- основной цикл ---
    while True:
        await asyncio.sleep(30)

        proxy_row = get_next_proxy()
        if not proxy_row:
            continue

        parser = AvitoParser(proxy=proxy_row["proxy"])
        items, status = await parser.parse_once(search_url)

        if status == 429:
            mark_proxy_banned(proxy_row["id"])
            continue

        if status != 200:
            continue

        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:

                for item in items:
                    await cursor.execute("""
                        INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, NOW())
                    """, (tg_id, item.id))

                    if cursor.rowcount == 0:
                        continue

                    await send_message(
                        tg_id,
                        f"📦 {item.title}\n💰 {item.price} ₽\n🔗 {item.url}"
                    )



def start_monitor(tg_id: int, url: str):
    if tg_id in active_monitors:
        return

    task = asyncio.create_task(monitor_worker(tg_id, url))
    active_monitors[tg_id] = task


def stop_monitor(tg_id: int):
    task = active_monitors.get(tg_id)
    if task:
        task.cancel()
