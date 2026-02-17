import asyncio
from datetime import datetime
from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message
from core.database import get_connection

active_monitors = {}


def get_next_proxy(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM proxies
            ORDER BY id ASC
        """)
        proxies = cursor.fetchall()

    if not proxies:
        return None

    proxy = proxies[int(datetime.now().timestamp()) % len(proxies)]
    return proxy["proxy"]


async def monitor_worker(tg_id: int, search_url: str):

    print(f"[MONITOR START] {tg_id}")

    connection = get_connection()

    try:
        # ---------- INIT PHASE ----------
        proxy = get_next_proxy(connection)
        parser = AvitoParser(proxy=proxy)

        items = parser.parse_once(search_url)

        for item in items:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO parsed_items (tg_id, item_id, created_at)
                    VALUES (%s, %s, %s)
                """, (tg_id, item.id, datetime.now()))
                connection.commit()

        print("[INIT DONE]")

        # ---------- MAIN LOOP ----------
        while True:

            await asyncio.sleep(30)

            print(f"[CHECKING NEW ITEMS] {tg_id}")

            proxy = get_next_proxy(connection)
            parser = AvitoParser(proxy=proxy)

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

                text = f"{item.title}\nЦена: {item.price} ₽\n{item.url}"

                print("[NEW ITEM FOUND]", item.id)
                send_message(tg_id, text)

    except asyncio.CancelledError:
        print(f"[MONITOR STOPPED] {tg_id}")

    except Exception as e:
        print("MONITOR ERROR:", e)

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
