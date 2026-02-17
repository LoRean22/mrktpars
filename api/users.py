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
# ADMIN
# ----------------------------

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
                INSERT INTO subscription_keys (`key`, subscription_type, expires_days, used)
                VALUES (%s, %s, %s, 0)
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
                INSERT INTO proxies (proxy, is_busy)
                VALUES (%s, 0)
            """, (data.proxy,))
            connection.commit()

        return {"status": "proxy added"}

    finally:
        connection.close()


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

        return {"total": total, "busy": busy}

    finally:
        connection.close()


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

            cursor.execute("""
                UPDATE users
                SET subscription_type=%s,
                    subscription_expires=%s,
                    trial_used=1
                WHERE tg_id=%s
            """, ("basic", expires, data.tg_id))

            connection.commit()

        return {"status": "trial activated"}

    finally:
        connection.close()


# ----------------------------
# RUN PARSER
# ----------------------------

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
                cursor.execute("""
                    UPDATE searches
                    SET search_url=%s, last_run=%s
                    WHERE user_id=%s
                """, (data.search_url, now, user_id))
            else:
                cursor.execute("""
                    INSERT INTO searches (user_id, search_url, last_run)
                    VALUES (%s, %s, %s)
                """, (user_id, data.search_url, now))

            connection.commit()

        # ---------- БЕРЕМ ПРОКСИ ----------
        proxy_value = None

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM proxies WHERE is_busy=0 LIMIT 1"
            )
            proxy_row = cursor.fetchone()
            

            if proxy_row:
                proxy_id = proxy_row["id"]
                proxy_value = proxy_row["proxy"]

                cursor.execute(
                    "UPDATE proxies SET is_busy=1 WHERE id=%s",
                    (proxy_id,)
                )
                connection.commit()
            else:
                print("Нет свободных прокси")
                return {"error": "Нет свободных прокси"}
            
            

        # ---------- ПАРСИНГ ----------
        parser = AvitoParser(proxy=proxy_value)
        items = parser.parse_once(data.search_url)

        sent = 0

        with connection.cursor() as cursor:
            for item in items:
                try:
                    # проверяем дубль по tg_id + item_id
                    cursor.execute("""
                        SELECT id FROM parsed_items
                        WHERE tg_id=%s AND item_id=%s
                    """, (data.tg_id, item.id))

                    exists = cursor.fetchone()
                    if exists:
                        continue

                    # вставляем под ТВОЮ структуру
                    cursor.execute("""
                        INSERT INTO parsed_items (tg_id, item_id, created_at)
                        VALUES (%s, %s, %s)
                    """, (data.tg_id, item.id, datetime.now()))

                    connection.commit()

                    text = f"{item.title}\n{item.url}"

                    print("SENDING TO TG:", data.tg_id)
                    print("TEXT:", text)

                    await send_message(data.tg_id, text)

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



        parser = AvitoParser(proxy=proxy_value)
        items = parser.parse_once(data.search_url)

        print("ITEMS COUNT:", len(items))


# ----------------------------
# ACTIVATE KEY
# ----------------------------

@router.post("/users/activate-key")
def activate_key(data: ActivateKey):

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

            cursor.execute(
                "SELECT * FROM subscription_keys WHERE `key`=%s",
                (data.key,)
            )
            key_row = cursor.fetchone()

            if not key_row:
                return {"error": "Ключ не найден"}

            if key_row["used"] == 1:
                return {"error": "Ключ уже использован"}

            expires = datetime.now() + timedelta(days=key_row["expires_days"])

            cursor.execute("""
                UPDATE users
                SET subscription_type=%s,
                    subscription_expires=%s
                WHERE tg_id=%s
            """, (key_row["subscription_type"], expires, data.tg_id))

            cursor.execute("""
                UPDATE subscription_keys
                SET used=1,
                    used_by=%s,
                    used_at=%s
                WHERE id=%s
            """, (user["id"], datetime.now(), key_row["id"]))

            connection.commit()

        return {"status": "activated"}

    finally:
        connection.close()
