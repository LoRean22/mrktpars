from fastapi import APIRouter
from pydantic import BaseModel
import pymysql
from datetime import datetime, timedelta

router = APIRouter()

# ----------------------------
# ПОДКЛЮЧЕНИЕ К БД
# ----------------------------

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="mrktpars_user",   # ⚠ если создавал нового пользователя
        password="StrongPassword123!",
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )

# ----------------------------
# MODELS
# ----------------------------

class InitUser(BaseModel):
    tg_id: int
    username: str | None = None


class TrialRequest(BaseModel):
    tg_id: int


class SaveSearch(BaseModel):
    tg_id: int
    search_url: str


class DeleteSearch(BaseModel):
    tg_id: int


# ----------------------------
# INIT USER
# ----------------------------

@router.post("/users/init")
def init_user(data: InitUser):
    print("🔥 Получен запрос:", data.dict())

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            print("👀 Найден пользователь:", user)

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

                print("✅ Пользователь создан")

        return {
            "subscription_type": user["subscription_type"],
            "subscription_expires": user["subscription_expires"]
        }

    finally:
        connection.close()


# ----------------------------
# TRIAL SUBSCRIPTION
# ----------------------------

@router.post("/users/trial")
def activate_trial(data: TrialRequest):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            if user["trial_used"] == 1:
                return {"error": "Вы уже использовали пробный период"}

            expires = datetime.now() + timedelta(days=2)

            cursor.execute(
                """
                UPDATE users
                SET subscription_type = %s,
                    subscription_expires = %s,
                    trial_used = 1
                WHERE tg_id = %s
                """,
                ("basic", expires, data.tg_id)
            )

            connection.commit()

        return {"status": "trial activated"}

    finally:
        connection.close()


# ----------------------------
# SAVE SEARCH
# ----------------------------

@router.post("/users/save-search")
def save_search(data: SaveSearch):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            user_id = user["id"]

            # удаляем старую ссылку
            cursor.execute(
                "DELETE FROM searches WHERE user_id = %s",
                (user_id,)
            )

            # вставляем новую
            cursor.execute(
                "INSERT INTO searches (user_id, search_url) VALUES (%s, %s)",
                (user_id, data.search_url)
            )

            connection.commit()

        return {"status": "saved"}

    finally:
        connection.close()


# ----------------------------
# DELETE SEARCH
# ----------------------------

@router.post("/users/delete-search")
def delete_search(data: DeleteSearch):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            cursor.execute(
                "DELETE FROM searches WHERE user_id = %s",
                (user["id"],)
            )

            connection.commit()

        return {"status": "deleted"}

    finally:
        connection.close()


# ----------------------------
# GET SEARCH
# ----------------------------

@router.post("/users/get-search")
def get_search(data: DeleteSearch):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE tg_id = %s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                return {"error": "User not found"}

            cursor.execute(
                "SELECT search_url FROM searches WHERE user_id = %s",
                (user["id"],)
            )

            search = cursor.fetchone()

        return search if search else {}

    finally:
        connection.close()
