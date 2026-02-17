import asyncio
import random
from datetime import datetime, timedelta
import pymysql
from loguru import logger

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


def update_proxy_health(proxy_id, status):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            if status == 200:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = LEAST(health_score + 1, 100)
                    WHERE id=%s
                """, (proxy_id,))
            elif status == 429:
                cursor.execute("""
                    UPDATE proxies
                    SET health_score = health_score - 20,
                        banned_until=%s
                    WHERE id=%s
                """, (datetime.now() + timedelta(minutes=2), proxy_id))

            connection.commit()

    finally:
        connection.close()


async def monitor_worker(tg_id: int, search_url: str):

    logger.info(f"[MONITOR START] {tg_id}")

    connection = get_connection()

    try:
        # INIT
        proxy_row = get_next_proxy()
        if not proxy_row:
            logger.error("No proxy available")
            return

        parser = AvitoParser(proxy=proxy_row["proxy"])
        items, status = parser.parse_once(search_url)

        update_proxy_health(proxy_row["id"], status)

        for item in items:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                    VALUES (%s, %s, %s)
                """, (tg_id, item.id, datetime.now()))
                connection.commit()

        # LOOP
        while True:
            sleep_time = random.uniform(30, 60)
            logger.info(f"[{tg_id}] Sleeping {round(sleep_time, 2)} sec")
            await asyncio.sleep(sleep_time)

            proxy_row = get_next_proxy()
            if not proxy_row:
                continue

            parser = AvitoParser(proxy=proxy_row["proxy"])
            items, status = parser.parse_once(search_url)

            update_proxy_health(proxy_row["id"], status)

            if status != 200:
                continue

            for item in items:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, %s)
                    """, (tg_id, item.id, datetime.now()))

                    if cursor.rowcount == 0:
                        continue

                    connection.commit()

                send_message(
                    tg_id,
                    f"📦 {item.title}\n💰 {item.price} ₽\n🔗 {item.url}"
                )

    except asyncio.CancelledError:
        logger.info(f"[MONITOR STOPPED] {tg_id}")

    finally:
        connection.close()
        active_monitors.pop(tg_id, None)


def start_monitor(tg_id: int, url: str):
    if tg_id in active_monitors:
        return

    task = asyncio.create_task(monitor_worker(tg_id, url))
    active_monitors[tg_id] = task


def stop_monitor(tg_id: int):
    task = active_monitors.get(tg_id)
    if task:
        task.cancel()
