import asyncio
import random
import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from loguru import logger

from core.browser_manager import browser_manager
from avito_parser.models import AvitoItem

MAX_ITEMS = 20


class AvitoParser:


    def __init__(self, tg_id: int, proxy: str | None = None):
        self.tg_id = tg_id
        self.proxy = proxy


    async def parse_once(self, url: str) -> Tuple[List[AvitoItem], int]:

        context = await browser_manager.get_context(self.tg_id, self.proxy)

        page = await context.new_page()

        try:
            await asyncio.sleep(random.uniform(1.0, 3.0))

            response = await page.goto(url, timeout=30000)
            status = response.status if response else 0

            logger.info(f"[PLAYWRIGHT] Status {status}")

            if status != 200:
                await page.close()
                return [], status

            await page.wait_for_timeout(random.uniform(1500, 3000))

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            cards = soup.select('[data-marker="item"]')[:MAX_ITEMS]

            items: List[AvitoItem] = []

            for card in cards:
                link = card.select_one('a[data-marker="item-title"]')
                if not link:
                    continue

                href = link.get("href")
                if not href:
                    continue

                if href.startswith("/"):
                    href = "https://www.avito.ru" + href

                m = re.search(r'_(\d+)$', href.split("?")[0])
                if not m:
                    continue

                item_id = m.group(1)
                title = link.get_text(strip=True)

                price_tag = card.select_one('[data-marker="item-price"]')
                price = 0
                if price_tag:
                    digits = "".join(c for c in price_tag.text if c.isdigit())
                    if digits:
                        price = int(digits)

                items.append(
                    AvitoItem(
                        id=item_id,
                        title=title,
                        price=price,
                        url=href
                    )
                )

            await page.close()
            return items, 200

        except Exception as e:
            logger.exception(f"[PLAYWRIGHT ERROR] {e}")
            await page.close()
            return [], 500
