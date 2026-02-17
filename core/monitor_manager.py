import asyncio
from datetime import datetime
import pymysql
import random


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

            return proxy["proxy"]

    finally:
        connection.close()


def format_message(item):
    return (
        f"📦 {item.title}\n"
        f"💰 {item.price} ₽\n\n"
        f"🔗 {item.url}"
    )


async def monitor_worker(tg_id: int, search_url: str):

    print(f"[MONITOR START] {tg_id}")

    connection = get_connection()

    try:
        proxy = get_next_proxy()
        if not proxy:
            print("NO PROXY")
            return

        # Sticky proxy + persistent session
        parser = AvitoParser(proxy=proxy)

        # прогрев без отправки
        items = parser.parse_once(search_url)
        for item in items:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                    VALUES (%s, %s, %s)
                """, (tg_id, item.id, datetime.now()))
                connection.commit()

        print(f"[INIT DONE] {tg_id}")

        while True:
            await asyncio.sleep(random.uniform(25, 40))

            items = parser.parse_once(search_url)

            for item in items:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM parsed_items
                        WHERE tg_id=%s AND item_id=%s
                    """, (tg_id, item.id))

                    exists = cursor.fetchone()
                    if exists:
                        continue

                    cursor.execute("""
                        INSERT INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, %s)
                    """, (tg_id, item.id, datetime.now()))
                    connection.commit()

                send_message(tg_id, format_message(item), item.image_url)

    except asyncio.CancelledError:
        print(f"[MONITOR STOPPED] {tg_id}")

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
