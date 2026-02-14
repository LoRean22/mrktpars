from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import pymysql

router = APIRouter()

# ----------------------------
# Модель входящих данных
# ----------------------------
class UserInit(BaseModel):
    tg_id: int
    username: str | None = None


# ----------------------------
# Подключение к MySQL
# ----------------------------
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",
        password="StrongPassword123!",  # твой пароль
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )


# ----------------------------
# Инициализация пользователя
# ----------------------------
@router.post("/users/init")
def init_user(data: UserInit):

    print("🔥 Получен запрос:", data.dict())

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # Проверяем есть ли пользователь
            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            print("👀 Найден пользователь:", user)

            # Если нет — создаём
            if not user:
                cursor.execute(
                    "INSERT INTO users (tg_id) VALUES (%s)",
                    (data.tg_id,)
                )
                connection.commit()

                print("✅ Пользователь создан")

                cursor.execute(
                    "SELECT * FROM users WHERE tg_id = %s",
                    (data.tg_id,)
                )
                user = cursor.fetchone()

        return {
            "subscription_type": user.get("subscription_type"),
            "subscription_expires": user.get("subscription_expires")
        }

    finally:
        connection.close()



@router.post("/users/trial")
def activate_trial(data: dict):
    tg_id = data.get("tg_id")

    if not tg_id:
        return {"error": "tg_id required"}

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "user not found"}

            if user["trial_used"]:
                return {"error": "trial already used"}

            expires = datetime.now() + timedelta(days=2)

            cursor.execute(
                """
                UPDATE users
                SET subscription_type = %s,
                    subscription_expires = %s,
                    trial_used = TRUE
                WHERE tg_id = %s
                """,
                ("basic", expires, tg_id)
            )
            connection.commit()

        return {
            "status": "trial activated",
            "subscription_type": "basic",
            "subscription_expires": expires
        }

    finally:
        connection.close()