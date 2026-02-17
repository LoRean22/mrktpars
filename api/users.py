from fastapi import APIRouter
from pydantic import BaseModel
import pymysql
import asyncio

from core.monitor_manager import monitor_worker, active_monitors

router = APIRouter()


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


class RunParser(BaseModel):
    tg_id: int
    search_url: str


@router.post("/users/run-parser")
async def run_parser(data: RunParser):

    print("START MONITOR REQUEST:", data.tg_id)

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE tg_id=%s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

        if not user:
            return {"error": "User not found"}

        # 1 пользователь = 1 ссылка
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM searches WHERE tg_id=%s", (data.tg_id,))
            cursor.execute("""
                INSERT INTO searches (tg_id, search_url, is_active)
                VALUES (%s, %s, 1)
            """, (data.tg_id, data.search_url))
            connection.commit()

        if data.tg_id in active_monitors:
            return {"status": "already running"}

        task = asyncio.create_task(
            monitor_worker(data.tg_id, data.search_url)
        )

        active_monitors[data.tg_id] = task

        return {"status": "monitor started"}

    finally:
        connection.close()
