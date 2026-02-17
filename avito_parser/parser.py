import random
import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from loguru import logger

from avito_parser.models import AvitoItem
from core.browser_manager import browser_manager

MAX_ITEMS = 20


class AvitoParser:

    async def parse_once(self, url: str, proxy: str | None = None) -> Tuple[List[AvitoItem], int]:

        context = await browser_manager.new_context(proxy)
        page = await context.new_page()

        # скрываем webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        try:
            logger.info(f"[PLAYWRIGHT] Opening {url}")

            response = await page.goto(url, wait_until="networkidle")

            status = response.status if response else 0
            logger.info(f"[PLAYWRIGHT] Status {status}")

            # имитация человека
            await page.wait_for_timeout(random.randint(2000, 4000))
            await page.mouse.move(random.randint(100, 400), random.randint(100, 400))
            await page.mouse.wheel(0, random.randint(400, 1200))
            await page.wait_for_timeout(random.randint(1000, 3000))

            html = await page.content()

            if status != 200:
                return [], status

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

            logger.info(f"[PLAYWRIGHT] Found {len(items)} items")

            return items, 200

        except Exception as e:
            logger.exception(f"[PLAYWRIGHT ERROR] {e}")
            return [], 500

        finally:
            await page.close()
            await context.close()
