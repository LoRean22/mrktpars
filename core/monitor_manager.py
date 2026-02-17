import asyncio
from datetime import datetime, timedelta
import pymysql

from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message


# -------------------------
# DB
# -------------------------

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


active_monitors = {}


# -------------------------
# PROXY SYSTEM
# -------------------------

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

        print(f"[PROXY BANNED] ID {proxy_id}")

    finally:
        connection.close()


# -------------------------
# MESSAGE FORMAT
# -------------------------

def format_message(item):
    return (
        f"📦 Название: {item.title}\n"
        f"💰 Цена: {item.price} ₽\n"
        f"🔗 Ссылка: {item.url}\n"
    )


# -------------------------
# MONITOR WORKER
# -------------------------

async def monitor_worker(tg_id: int, search_url: str):

    print(f"[MONITOR START] {tg_id}")

    connection = get_connection()

    try:
        # -------- ПРОГРЕВ --------
        proxy_row = get_next_proxy()
        if not proxy_row:
            print("NO PROXY FOR INIT")
            return

        parser = AvitoParser(proxy=proxy_row["proxy"])
        items = parser.parse_once(search_url)

        for item in items:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                    VALUES (%s, %s, %s)
                """, (tg_id, item.id, datetime.now()))
                connection.commit()

        print(f"[MONITOR INIT DONE] {tg_id}")

        # -------- ОСНОВНОЙ ЦИКЛ --------
        while True:
            await asyncio.sleep(30)

            retry_count = 0
            items = []

            while retry_count < 5:
                proxy_row = get_next_proxy()

                if not proxy_row:
                    print("NO AVAILABLE PROXY")
                    break

                proxy_id = proxy_row["id"]
                proxy_value = proxy_row["proxy"]

                print(f"[{tg_id}] Using proxy:", proxy_value)

                parser = AvitoParser(proxy=proxy_value)
                items = parser.parse_once(search_url)

                if items == []:
                    print(f"[{tg_id}] Proxy likely banned:", proxy_value)
                    mark_proxy_banned(proxy_id)
                    retry_count += 1
                    continue

                break

            if retry_count == 5:
                print("ALL PROXIES FAILED")
                continue

            # -------- отправка новых --------
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

                text = format_message(item)
                print(f"[{tg_id}] NEW ITEM:", item.id)
                send_message(tg_id, text)

    except asyncio.CancelledError:
        print(f"[MONITOR STOPPED] {tg_id}")

    except Exception as e:
        print("MONITOR ERROR:", e)

    finally:
        connection.close()
        active_monitors.pop(tg_id, None)


# -------------------------
# START / STOP
# -------------------------

def start_monitor(tg_id: int, url: str):
    if tg_id in active_monitors:
        return

    task = asyncio.create_task(monitor_worker(tg_id, url))
    active_monitors[tg_id] = task


def stop_monitor(tg_id: int):
    task = active_monitors.get(tg_id)
    if task:
        task.cancel()
