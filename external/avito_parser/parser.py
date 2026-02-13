from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from external.avito_parser.playwright_client import AvitoPlaywrightClient
from external.avito_parser.models import AvitoItem


class AvitoParser:
    """
    ASYNC Avito парсер.
    1 вызов = 1 проход.
    """

    def __init__(self, proxy: str | None = None):
        self.client = AvitoPlaywrightClient(proxy=proxy)

    async def parse_once(self, search_url: str) -> List[AvitoItem]:
        logger.info(f"AvitoParser: начинаю парсинг {search_url}")

        html = await self.client.get_html(search_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[AvitoItem] = []
        cards = soup.select(
            '[data-marker="item"], div[data-item-id]'
        )


        logger.info(f"AvitoParser: найдено карточек: {len(cards)}")

        for card in cards:
            try:
                item_id = card.get("data-item-id")
                if not item_id:
                    continue

                title_tag = card.select_one('[data-marker="item-title"]')
                title = title_tag.text.strip() if title_tag else "Без названия"

                price = 0
                price_tag = card.select_one('[data-marker="item-price"]')
                if price_tag:
                    digits = "".join(c for c in price_tag.text if c.isdigit())
                    if digits:
                        price = int(digits)

                link_tag = card.select_one('a[data-marker="item-title"]')
                if not link_tag or not link_tag.get("href"):
                    continue

                url = link_tag["href"]
                if url.startswith("/"):
                    url = "https://www.avito.ru" + url

                items.append(
                    AvitoItem(
                        id=str(item_id),
                        title=title,
                        price=price,
                        url=url,
                    )
                )

            except Exception:
                logger.exception("Ошибка при разборе карточки")

        logger.info(f"AvitoParser: успешно разобрано {len(items)} объявлений")
        return items
