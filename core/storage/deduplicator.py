from loguru import logger
from typing import Set


class Deduplicator:
    """
    Хранит ID объявлений, которые уже были обработаны
    """

    def __init__(self):
        self.seen_ids: Set[str] = set()

    def is_new(self, item_id: str) -> bool:
        """
        Проверяет, новое ли объявление
        """
        return item_id not in self.seen_ids

    def mark_seen(self, item_id: str):
        """
        Помечает объявление как обработанное
        """
        self.seen_ids.add(item_id)
        logger.debug(f"ID {item_id} сохранён в дедупликаторе")

    def stats(self) -> int:
        return len(self.seen_ids)
