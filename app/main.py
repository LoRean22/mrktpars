from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymysql
from datetime import datetime

app = FastAPI()

# ----------------------------
# CORS (чтобы Mini App работал)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Подключение к MySQL
# ----------------------------
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",          # если другой — поменяй
        password="mysql199300_",  # 🔥 ВСТАВЬ СВОЙ ПАРОЛЬ
        database="mrktpars",
        cursorclass=pymysql.cursors.DictCursor
    )

# ----------------------------
# Инициализация пользователя
# ----------------------------
@app.post("/users/init")
def init_user(data: dict):
    tg_id = data.get("tg_id")
    username = data.get("username")

    if not tg_id:
        return {"error": "tg_id required"}

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            # Проверяем есть ли пользователь
            cursor.execute(
                "SELECT * FROM users WHERE tg_id = %s",
                (tg_id,)
            )
            user = cursor.fetchone()

            # Если нет — создаём
            if not user:
                cursor.execute(
                    "INSERT INTO users (tg_id) VALUES (%s)",
                    (tg_id,)
                )
                connection.commit()

                cursor.execute(
                    "SELECT * FROM users WHERE tg_id = %s",
                    (tg_id,)
                )
                user = cursor.fetchone()

        return {
            "subscription_type": user["subscription_type"],
            "subscription_expires": user["subscription_expires"]
        }

    finally:
        connection.close()


# ----------------------------
# Проверка сервера
# ----------------------------
@app.get("/")
def root():
    return {"status": "MRKTPARS backend running"}
