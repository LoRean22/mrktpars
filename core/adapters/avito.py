from typing import List, Dict
from loguru import logger

from external.avito_parser.parser import AvitoParser
from external.avito_parser.models import AvitoItem


class AvitoAdapter:
    """
    Async-адаптер над AvitoParser.
    Используется executor'ом.
    """

    def __init__(self, proxy: str | None = None):
        self.parser = AvitoParser(proxy=proxy)
        logger.info("AvitoAdapter: инициализирован async AvitoParser")

    async def parse(self, search_url: str) -> List[Dict]:
        """
        Делает ОДИН async-проход по Avito
        и возвращает объявления в виде dict
        """

        items: List[AvitoItem] = await self.parser.parse_once(search_url)

        results: List[Dict] = []

        for item in items:
            results.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "price": item.price,
                    "url": item.url,
                }
            )

        logger.info(
            f"AvitoAdapter: возвращено объявлений: {len(results)}"
        )

        return results
