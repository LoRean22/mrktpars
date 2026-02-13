from fastapi import FastAPI
from app.api import users, searches
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(searches.router)

@app.get("/health")
def health():
    return {"status": "ok"}
