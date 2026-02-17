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



class AdminKey(BaseModel):
    tg_id: int
    subscription_type: str
    expires_days: int

class AddProxy(BaseModel):
    tg_id: int
    proxy: str

def is_admin(tg_id: int):
    return tg_id == ADMIN_TG_ID


@router.post("/admin/create-key")
def create_key(data: AdminKey):

    if not is_admin(data.tg_id):
        return {"error": "Not allowed"}

    import secrets

    new_key = secrets.token_hex(16)

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO subscription_keys (`key`, subscription_type, expires_days)
                VALUES (%s, %s, %s)
            """, (new_key, data.subscription_type, data.expires_days))
            connection.commit()

        return {"key": new_key}

    finally:
        connection.close()


@router.post("/admin/add-proxy")
def add_proxy(data: AddProxy):

    if not is_admin(data.tg_id):
        return {"error": "Not allowed"}

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO proxies (proxy)
                VALUES (%s)
            """, (data.proxy,))
            connection.commit()

        return {"status": "proxy added"}

    finally:
        connection.close()


@router.post("/admin/proxy-stats")
class AdminRequest(BaseModel):
    tg_id: int

@router.post("/admin/proxy-stats")
def proxy_stats(data: AdminRequest):


    if not is_admin(data.tg_id):
        return {"error": "Not allowed"}

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM proxies")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as busy FROM proxies WHERE is_busy=1")
            busy = cursor.fetchone()["busy"]

        return {
            "total": total,
            "busy": busy
        }

    finally:
        connection.close()


# ----------------------------
# MODELS
# ----------------------------

class InitUser(BaseModel):
    tg_id: int
    username: str | None = None


class TrialRequest(BaseModel):
    tg_id: int


class RunParser(BaseModel):
    tg_id: int
    search_url: str


# ----------------------------
# INIT USER
# ----------------------------

@router.post("/users/init")
def init_user(data: InitUser):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM users WHERE tg_id=%s",
                (data.tg_id,)
            )
            user = cursor.fetchone()

            if not user:
                cursor.execute(
                    "INSERT INTO users (tg_id) VALUES (%s)",
                    (data.tg_id,)
                )
                connection.commit()

                cursor.execute(
                    "SELECT * FROM users WHERE tg_id=%s",
                    (data.tg_id,)
                )
                user = cursor.fetchone()

        return {
            "subscription_type": user["subscription_type"],
            "subscription_expires": user["subscription_expires"]
        }

    finally:
        connection.close()


# ----------------------------
# TRIAL
# ----------------------------

@router.post("/users/trial")
def activate_trial(data: TrialRequest):

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

            if user["trial_used"] == 1:
                return {"error": "Вы уже использовали пробный период"}

            expires = datetime.now() + timedelta(days=2)

            cursor.execute(
                """
                UPDATE users
                SET subscription_type=%s,
                    subscription_expires=%s,
                    trial_used=1
                WHERE tg_id=%s
                """,
                ("basic", expires, data.tg_id)
            )

            connection.commit()

        return {"status": "trial activated"}

    finally:
        connection.close()


# ----------------------------
# RUN PARSER
# ----------------------------

@router.post("/users/run-parser")
async def run_parser(data: RunParser):

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

            user_id = user["id"]

            now = datetime.now()

            cursor.execute(
                "SELECT * FROM searches WHERE user_id=%s",
                (user_id,)
            )
            search = cursor.fetchone()

            if search and search["last_run"]:
                if now - search["last_run"] < timedelta(minutes=1):
                    return {"error": "Подождите 1 минуту"}

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
                    VALUES (%s,%s,%s)
                    """,
                    (user_id, data.search_url, now)
                )

            connection.commit()

        # 🔥 Запуск парсера
        parser = AvitoParser()
        items = await parser.parse_once(data.search_url)

        sent = 0

        with connection.cursor() as cursor:
            for item in items:

                try:
                    cursor.execute(
                        """
                        INSERT INTO parsed_items (user_id, item_id)
                        VALUES (%s,%s)
                        """,
                        (user_id, item.id)
                    )
                    connection.commit()

                    text = f"{item.title}\n{item.url}"
                    await send_message(data.tg_id, text)

                    sent += 1

                except:
                    continue

        return {"status": "ok", "sent": sent}

    finally:
        connection.close()
