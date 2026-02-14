from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import users

app = FastAPI()

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Подключаем роутеры
# ----------------------------
app.include_router(users.router)

# ----------------------------
# Проверка сервера
# ----------------------------
@app.get("/")
def root():
    return {"status": "MRKTPARS backend running"}
