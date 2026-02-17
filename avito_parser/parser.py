import asyncio
import random
import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode

from loguru import logger
from core.http_client import http_session

from avito_parser.models import AvitoItem

MAX_ITEMS = 20


def get_headers():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        ]),
        "Accept-Language": "ru-RU,ru;q=0.9",
    }


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    async def parse_once(self, url: str) -> Tuple[List[AvitoItem], int]:

        await asyncio.sleep(random.uniform(0.8, 1.5))  # возвращаем human delay

        url = self.clean_url(url)

        proxy_url = None
        if self.proxy:
            parts = self.proxy.split(":")
            if len(parts) == 4:
                ip, port, login, password = parts
                proxy_url = f"http://{login}:{password}@{ip}:{port}"
            elif len(parts) == 2:
                ip, port = parts
                proxy_url = f"http://{ip}:{port}"

        logger.info(f"[PARSER] {url}")
        if proxy_url:
            logger.info(f"[PARSER] Proxy {proxy_url}")

        try:
            async with http_session.get(
                url,
                headers=get_headers(),
                proxy=proxy_url
            ) as response:

                status = response.status
                logger.info(f"[PARSER] Status {status}")

                if status != 200:
                    return [], status

                text = await response.text()

                if "Доступ ограничен" in text:
                    return [], 403

                soup = BeautifulSoup(text, "lxml")
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

                logger.info(f"[PARSER] Found {len(items)} items")

                return items, 200

        except asyncio.TimeoutError:
            logger.warning("[PARSER] Timeout")
            return [], 408
        except Exception as e:
            logger.exception(f"[PARSER] Error: {e}")
            return [], 500
