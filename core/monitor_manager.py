import asyncio
from datetime import datetime
import random
import pymysql
from typing import Optional, Set

from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message


# -------------------------------------------------
# DB CONFIG
# -------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "user": "mrktpars_user",
    "password": "StrongPassword123!",
    "database": "mrktpars",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


# -------------------------------------------------
# ACTIVE TASKS
# -------------------------------------------------

active_monitors: dict[int, asyncio.Task] = {}


# -------------------------------------------------
# PROXY ROTATION
# -------------------------------------------------

def get_next_proxy() -> Optional[str]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, proxy FROM proxies
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
            """, (datetime.utcnow(), proxy["id"]))

            return proxy["proxy"]
    finally:
        connection.close()


# -------------------------------------------------
# DB HELPERS
# -------------------------------------------------

def get_known_ids(tg_id: int) -> Set[str]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT item_id FROM parsed_items
                WHERE tg_id=%s
            """, (tg_id,))
            return {row["item_id"] for row in cursor.fetchall()}
    finally:
        connection.close()


def save_item(tg_id: int, item_id: str):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                VALUES (%s, %s, %s)
            """, (tg_id, item_id, datetime.utcnow()))
    finally:
        connection.close()


# -------------------------------------------------
# MESSAGE FORMAT
# -------------------------------------------------

def format_message(item) -> str:
    return (
        f"<b>{item.title}</b>\n"
        f"💰 {item.price} ₽\n\n"
        f"<a href='{item.url}'>Открыть объявление</a>"
    )


# -------------------------------------------------
# MONITOR WORKER
# -------------------------------------------------

async def monitor_worker(tg_id: int, search_url: str):

    print(f"[MONITOR START] {tg_id}")
    first_run = True
    parser: Optional[AvitoParser] = None

    try:
        while True:

            # --- создаём парсер если его нет ---
            if not parser:
                proxy = await asyncio.to_thread(get_next_proxy)

                if not proxy:
                    print("NO PROXY AVAILABLE")
                    await asyncio.sleep(10)
                    continue

                print(f"[{tg_id}] USING PROXY {proxy}")
                parser = AvitoParser(proxy=proxy)

                await asyncio.sleep(random.uniform(2, 5))

            # --- получаем ID ---
            id_list, status = await asyncio.to_thread(
                parser.parse_once, search_url
            )

            # --- обработка 429 ---
            if status == 429:
                print(f"[{tg_id}] 429 → switching proxy")
                parser.close()
                parser = None
                await asyncio.sleep(random.uniform(5, 10))
                continue

            if status != 200:
                await asyncio.sleep(random.uniform(10, 15))
                continue

            known_ids = await asyncio.to_thread(get_known_ids, tg_id)

            # --- FIRST RUN ---
            if first_run:
                for item_id, _ in id_list:
                    await asyncio.to_thread(save_item, tg_id, item_id)

                first_run = False
                await asyncio.sleep(random.uniform(30, 40))
                continue

            # --- новые объявления ---
            for item_id, href in id_list:

                if item_id in known_ids:
                    break

                full_item = await asyncio.to_thread(
                    parser.parse_full_item, item_id, href
                )

                if not full_item:
                    continue

                await asyncio.to_thread(save_item, tg_id, item_id)

                try:
                    await asyncio.to_thread(
                        send_message,
                        tg_id,
                        format_message(full_item),
                        full_item.image_url
                    )
                except Exception as e:
                    print("TG ERROR:", e)

            await asyncio.sleep(random.uniform(30, 45))

    except asyncio.CancelledError:
        print(f"[MONITOR STOPPED] {tg_id}")

    finally:
        if parser:
            parser.close()
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
