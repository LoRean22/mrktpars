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


# -------------------------------------------------
# PROXY ROTATION
# -------------------------------------------------

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


# -------------------------------------------------
# MESSAGE FORMAT
# -------------------------------------------------

def format_message(item):
    return (
        f"📦 {item.title}\n"
        f"💰 {item.price} ₽\n\n"
        f"🔗 {item.url}"
    )


# -------------------------------------------------
# MONITOR WORKER
# -------------------------------------------------

async def monitor_worker(tg_id: int, search_url: str):

    print(f"[MONITOR START] {tg_id}")

    connection = get_connection()

    try:
        parser = None

        while True:

            # ---- если нет парсера → берём прокси ----
            if not parser:
                proxy = get_next_proxy()

                if not proxy:
                    print("NO PROXY")
                    await asyncio.sleep(10)
                    continue

                print(f"[{tg_id}] USING PROXY {proxy}")
                parser = AvitoParser(proxy=proxy)

                await asyncio.sleep(random.uniform(3, 6))

            # ---- получаем уже известные ID один раз ----
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT item_id FROM parsed_items
                    WHERE tg_id=%s
                """, (tg_id,))
                known_ids = {row["item_id"] for row in cursor.fetchall()}

            items, status = parser.parse_once(search_url)

            # ---- обработка 429 ----
            if status == 429:
                print(f"[{tg_id}] 429 DETECTED → switching proxy")
                parser = None
                await asyncio.sleep(random.uniform(5, 10))
                continue

            if status != 200:
                print(f"[{tg_id}] Status {status}")
                await asyncio.sleep(random.uniform(10, 15))
                continue

            # ---- обработка новых объявлений ----
            for item in items:

                # если объявление старое — прекращаем цикл
                if item.id in known_ids:
                    break

                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, %s)
                    """, (tg_id, item.id, datetime.now()))
                    connection.commit()

                print(f"[{tg_id}] NEW ITEM:", item.id)

                send_message(
                    tg_id,
                    format_message(item),
                    item.image_url
                )

            # ---- человекоподобная пауза ----
            await asyncio.sleep(random.uniform(25, 35))

    except asyncio.CancelledError:
        print(f"[MONITOR STOPPED] {tg_id}")

    finally:
        connection.close()
        active_monitors.pop(tg_id, None)


# -------------------------------------------------
# START / STOP
# -------------------------------------------------

def start_monitor(tg_id: int, url: str):
    if tg_id in active_monitors:
        return

    task = asyncio.create_task(monitor_worker(tg_id, url))
    active_monitors[tg_id] = task


def stop_monitor(tg_id: int):
    task = active_monitors.get(tg_id)
    if task:
        task.cancel()
