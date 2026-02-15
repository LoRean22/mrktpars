from fastapi import APIRouter
from pydantic import BaseModel
import pymysql
from datetime import datetime, timedelta
from avito_parser.parser import AvitoParser
from core.telegram_sender import send_message
import asyncio

router = APIRouter()


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

class RunParser(BaseModel):
    tg_id: int
    search_url: str


# ----------------------------
# RUN PARSER
# ----------------------------

@router.post("/users/run-parser")
async def run_parser(data: RunParser):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # Получаем пользователя
            cursor.execute(
                "SELECT * FROM users WHERE tg_id=%s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            user_id = user["id"]

            # Проверяем cooldown
            cursor.execute(
                "SELECT * FROM searches WHERE user_id=%s",
                (user_id,)
            )
            search = cursor.fetchone()

            now = datetime.now()

            if search and search["last_run"]:
                if now - search["last_run"] < timedelta(minutes=1):
                    return {"error": "Подождите 1 минуту"}

            # Обновляем или создаем запись
            if search:
                cursor.execute(
                    """
                    UPDATE searches
                    SET search_url=%s, last_run=%s
                    WHERE user_id=%s
                    """,
                    (data.search_url, now, user_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO searches (user_id, search_url, last_run)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, data.search_url, now)
                )

            connection.commit()

        # 🔥 Запускаем парсер
        parser = AvitoParser()
        items = await parser.parse_once(data.search_url)

        sent = 0

        with connection.cursor() as cursor:
            for item in items:

                try:
                    cursor.execute(
                        """
                        SELECT id FROM parsed_items
                        WHERE user_id=%s AND item_id=%s
                        """,
                        (user_id, item.id)
                    )

                    exists = cursor.fetchone()

                    if exists:
                        continue

                    cursor.execute(
                        """
                        INSERT INTO parsed_items (user_id, item_id)
                        VALUES (%s, %s)
                        """,
                        (user_id, item.id)
                    )
                    connection.commit()

                    text = f"{item.title}\n{item.url}"
                    await send_message(data.tg_id, text)

                    sent += 1


                    sent += 1

                except:
                    continue

        return {"status": "ok", "sent": sent}

    finally:
        connection.close()
