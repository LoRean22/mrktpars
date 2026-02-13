from loguru import logger
from core.db import get_connection


def save_item(task_id: int, user_id: int, title: str, price: int, url: str) -> bool:
    """
    Сохраняет объявление.
    Возвращает True если НОВОЕ, False если дубль
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT IGNORE INTO items (task_id, user_id, title, price, url)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (task_id, user_id, title, price, url)
            )
            conn.commit()

            if cur.rowcount == 0:
                return False  # дубль

            return True  # новое
    except Exception as e:
        logger.error(f"Ошибка сохранения объявления: {e}")
        return False
    finally:
        conn.close()
