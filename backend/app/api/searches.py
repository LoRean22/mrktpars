from fastapi import APIRouter
from app.db import get_connection

router = APIRouter(prefix="/api/searches", tags=["searches"])

@router.post("")
def create_search(data: dict):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO searches (user_id, search_url, interval_sec)
        VALUES (%s,%s,%s)
    """, (
        data["user_id"],
        data["search_url"],
        data.get("interval", 25)
    ))

    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok"}
