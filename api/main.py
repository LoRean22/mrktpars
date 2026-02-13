from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.users import router as users_router
from api.searches import router as searches_router

app = FastAPI(title="MrktPars API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для локальных тестов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api")
app.include_router(searches_router, prefix="/api")
