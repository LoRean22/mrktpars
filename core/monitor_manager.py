import asyncio
from loguru import logger
from datetime import datetime, timedelta
import pymysql

import random

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


# =========================
# PROXY SYSTEM
# =========================

def get_next_proxy():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proxies
                WHERE (is_banned=0 OR banned_until < NOW() OR banned_until IS NULL)
                ORDER BY health_score DESC, last_used_at ASC
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


def update_proxy_health(proxy_id, status):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            if status == 200:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = LEAST(health_score + 1, 100),
                        success_count = success_count + 1
                    WHERE id=%s
                """, (proxy_id,))

            elif status == 429:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = health_score - 25,
                        fail_count = fail_count + 1
                    WHERE id=%s
                """, (proxy_id,))

            elif status == 403:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = health_score - 20,
                        fail_count = fail_count + 1
                    WHERE id=%s
                """, (proxy_id,))

            else:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = health_score - 10,
                        fail_count = fail_count + 1
                    WHERE id=%s
                """, (proxy_id,))

            # Проверяем здоровье
            cursor.execute("SELECT health_score FROM proxies WHERE id=%s", (proxy_id,))
            row = cursor.fetchone()

            if row and row["health_score"] <= 20:
                logger.warning(f"[PROXY] Proxy {proxy_id} health <= 20 → banning 3 min")

                cursor.execute("""
                    UPDATE proxies
                    SET is_banned=1,
                        banned_until=%s
                    WHERE id=%s
                """, (datetime.now() + timedelta(minutes=3), proxy_id))

            connection.commit()

    finally:
        connection.close()


# =========================
# MESSAGE
# =========================

def format_message(item):
    return (
        f"📦 {item.title}\n"
        f"💰 {item.price} ₽\n"
        f"🔗 {item.url}\n"
    )


# =========================
# MONITOR WORKER
# =========================

async def monitor_worker(tg_id: int, search_url: str):

    logger.info(f"[MONITOR START] {tg_id}")

    pool = await get_pool()

    try:
        # ---------- INIT (ждём прокси если нет) ----------
        while True:
            proxy_row = get_next_proxy()

            if proxy_row:
                break

            logger.warning("No proxy available for init → waiting 10 sec")
            await asyncio.sleep(10)

        logger.info(f"[{tg_id}] INIT proxy {proxy_row['proxy']}")

        parser = AvitoParser(tg_id)

        items, status = await parser.parse_once(search_url)

        update_proxy_health(proxy_row["id"], status)

        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                for item in items:
                    await cursor.execute("""
                        INSERT INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, NOW())
                        ON DUPLICATE KEY UPDATE item_id = item_id
                    """, (tg_id, item.id))


        # ---------- MAIN LOOP ----------
        while True:
            sleep_time = random.uniform(20, 40)
            logger.info(f"[{tg_id}] Sleeping {round(sleep_time, 2)} sec")
            await asyncio.sleep(sleep_time)


            proxy_row = get_next_proxy()
            if not proxy_row:
                logger.warning("No available proxy → waiting")
                continue

            logger.info(f"[{tg_id}] Using proxy {proxy_row['proxy']}")

            parser = AvitoParser(proxy=proxy_row["proxy"])
            items, status = await parser.parse_once(search_url)

            update_proxy_health(proxy_row["id"], status)

            if status == 429:
                logger.warning(f"[{tg_id}] 429 → proxy health reduced")
                continue

            if status != 200:
                logger.warning(f"[{tg_id}] Non-200 status: {status}")
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

                        logger.success(f"[{tg_id}] NEW ITEM {item.id}")

                        await send_message(
                            tg_id,
                            format_message(item)
                        )

    except asyncio.CancelledError:
        logger.info(f"[MONITOR STOPPED] {tg_id}")

    except Exception as e:
        logger.exception(f"[MONITOR ERROR] {e}")

    finally:
        active_monitors.pop(tg_id, None)


# =========================
# START / STOP
# =========================

def start_monitor(tg_id: int, url: str):
    if tg_id in active_monitors:
        logger.warning(f"Monitor already running for {tg_id}")
        return

    task = asyncio.create_task(monitor_worker(tg_id, url))
    active_monitors[tg_id] = task


def stop_monitor(tg_id: int):
    task = active_monitors.get(tg_id)
    if task:
        task.cancel()
