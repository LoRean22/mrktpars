import asyncio
from datetime import datetime
import pymysql
from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message


active_monitors = {}  # tg_id -> asyncio.Task


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


async def monitor_worker(tg_id: int, search_url: str):
    print(f"[MONITOR START] {tg_id}")

    proxy_index = 0
    first_run = True

    while True:
        try:
            connection = get_connection()

            # ---- получаем все прокси ----
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM proxies")
                proxies = cursor.fetchall()

            if not proxies:
                print("NO PROXIES")
                await asyncio.sleep(30)
                continue

            proxy = proxies[proxy_index % len(proxies)]["proxy"]
            proxy_index += 1

            print(f"[{tg_id}] Using proxy: {proxy}")

            parser = AvitoParser(proxy=proxy)
            items = parser.parse_once(search_url)

            print(f"[{tg_id}] Items parsed:", len(items))

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

                # если это первый запуск — не отправляем
                if first_run:
                    continue

                text = f"{item.title}\n{item.url}"
                send_message(tg_id, text)

            if first_run:
                print(f"[{tg_id}] First run completed. Monitoring started.")
                first_run = False

            connection.close()

        except Exception as e:
            print(f"[{tg_id}] MONITOR ERROR:", e)

        await asyncio.sleep(30)
