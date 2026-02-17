from fastapi import APIRouter
from pydantic import BaseModel
import pymysql
from datetime import datetime, timedelta
from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message

router = APIRouter()

ADMIN_TG_ID = 5849724815


# ----------------------------
# DB CONNECTION
# ----------------------------

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


# ----------------------------
# MODELS
# ----------------------------

class ActivateKey(BaseModel):
    tg_id: int
    key: str


class AdminKey(BaseModel):
    tg_id: int
    subscription_type: str
    expires_days: int


class AddProxy(BaseModel):
    tg_id: int
    proxy: str


class AdminRequest(BaseModel):
    tg_id: int


class InitUser(BaseModel):
    tg_id: int
    username: str | None = None


class TrialRequest(BaseModel):
    tg_id: int


class RunParser(BaseModel):
    tg_id: int
    search_url: str


def is_admin(tg_id: int):
    return tg_id == ADMIN_TG_ID


# ----------------------------
# RUN PARSER
# ----------------------------

@router.post("/users/run-parser")
async def run_parser(data: RunParser):

    print("RUN_PARSER CALLED")

    connection = get_connection()
    proxy_id = None

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM users WHERE tg_id=%s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            now = datetime.now()

            # ---------- ПРОВЕРКА ПЕРЕЗАПУСКА ----------
            cursor.execute(
                "SELECT * FROM searches WHERE tg_id=%s",
                (data.tg_id,)
            )
            search = cursor.fetchone()

            if search and search["last_run"]:
                if now - search["last_run"] < timedelta(minutes=1):
                    return {"error": "Подождите 1 минуту"}

            if search:
                cursor.execute("""
                    UPDATE searches
                    SET search_url=%s, last_run=%s
                    WHERE tg_id=%s
                """, (data.search_url, now, data.tg_id))
            else:
                cursor.execute("""
                    INSERT INTO searches (tg_id, search_url, last_run)
                    VALUES (%s, %s, %s)
                """, (data.tg_id, data.search_url, now))

            connection.commit()

        # ---------- БЕРЕМ ПРОКСИ ----------
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM proxies WHERE is_busy=0 LIMIT 1"
            )
            proxy_row = cursor.fetchone()

            if not proxy_row:
                return {"error": "Нет свободных прокси"}

            proxy_id = proxy_row["id"]
            proxy_value = proxy_row["proxy"]

            cursor.execute(
                "UPDATE proxies SET is_busy=1 WHERE id=%s",
                (proxy_id,)
            )
            connection.commit()

        # ---------- ПАРСИНГ ----------
        parser = AvitoParser(proxy=proxy_value)
        items = parser.parse_once(data.search_url)

        print("ITEMS FOUND:", len(items))

        sent = 0

        with connection.cursor() as cursor:
            for item in items:
                try:
                    # Проверяем дубликат
                    cursor.execute("""
                        SELECT id FROM parsed_items
                        WHERE tg_id=%s AND item_id=%s
                    """, (data.tg_id, item.id))

                    if cursor.fetchone():
                        continue

                    # Вставляем
                    cursor.execute("""
                        INSERT INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, NOW())
                    """, (data.tg_id, item.id))

                    connection.commit()

                    text = f"{item.title}\n{item.url}"

                    print("SENDING TO TG:", data.tg_id)
                    print("TEXT:", text)

                    send_message(data.tg_id, text)

                    sent += 1

                except Exception as e:
                    print("SEND ERROR:", e)

        return {"status": "ok", "sent": sent}

    finally:
        if proxy_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE proxies SET is_busy=0 WHERE id=%s",
                    (proxy_id,)
                )
                connection.commit()

        connection.close()
