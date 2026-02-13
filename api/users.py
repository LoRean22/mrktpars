from fastapi import APIRouter
from pydantic import BaseModel
import pymysql

router = APIRouter()

class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="mysql199300_",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


@router.post("/users/init")
def init_user(user: UserCreate):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:

            # Проверяем существует ли пользователь
            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (user.telegram_id,)
            )
            existing = cursor.fetchone()

            if not existing:
                cursor.execute(
                    """
                    INSERT INTO users (tg_id)
                    VALUES (%s)
                    """,
                    (user.telegram_id,)
                )
                connection.commit()

        return {"status": "ok"}

    finally:
        connection.close()
