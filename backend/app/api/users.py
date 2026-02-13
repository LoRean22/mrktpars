from fastapi import APIRouter
from app.db import get_connection

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("")
def create_user(data: dict):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (id, username, first_name, last_name)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
        username=VALUES(username),
        first_name=VALUES(first_name),
        last_name=VALUES(last_name)
    """, (
        data["telegram_id"],
        data.get("username"),
        data.get("first_name"),
        data.get("last_name")
    ))

    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}
