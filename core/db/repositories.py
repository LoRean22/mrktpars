from core.db.connection import get_connection


class SeenAdsRepository:
    def is_new(self, search_id: int, avito_id: str) -> bool:
        with get_connection().cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM seen_ads WHERE search_id=%s AND avito_id=%s",
                (search_id, avito_id),
            )
            return cursor.fetchone() is None

    def mark_seen(self, search_id: int, avito_id: str):
        with get_connection().cursor() as cursor:
            cursor.execute(
                "INSERT IGNORE INTO seen_ads (search_id, avito_id) VALUES (%s, %s)",
                (search_id, avito_id),
            )
