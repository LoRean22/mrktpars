from fastapi import APIRouter
from pydantic import BaseModel
import pymysql

router = APIRouter()


class UserInit(BaseModel):
    tg_id: int
    username: str | None = None


def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="mysql199300_",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


@router.post("/users/init")
def init_user(data: UserInit):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # Проверяем есть ли пользователь
            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            # Если нет — создаём
            if not user:
                cursor.execute(
                    "INSERT INTO users (tg_id) VALUES (%s)",
                    (data.tg_id,)
                )
                connection.commit()

                cursor.execute(
                    "SELECT * FROM users WHERE tg_id = %s",
                    (data.tg_id,)
                )
                user = cursor.fetchone()

        return {
            "subscription_type": user["subscription_type"],
            "subscription_expires": user["subscription_expires"]
        }

    finally:
        connection.close()
