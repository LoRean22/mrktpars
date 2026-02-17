import requests
import random
import re
import time
from typing import List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
from loguru import logger

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
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(get_headers())

        if proxy:
            parts = proxy.split(":")
            if len(parts) == 4:
                ip, port, login, password = parts
                proxy_url = f"http://{login}:{password}@{ip}:{port}"
            elif len(parts) == 2:
                ip, port = parts
                proxy_url = f"http://{ip}:{port}"
            else:
                raise ValueError("Invalid proxy format")

            self.session.proxies.update({
                "http": proxy_url,
                "https": proxy_url
            })

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    def parse_once(self, url: str) -> Tuple[List[AvitoItem], int]:

        url = self.clean_url(url)

        try:
            time.sleep(random.uniform(1.0, 2.5))  # анти-детект

            response = self.session.get(url, timeout=20)

            status = response.status_code
            logger.info(f"[REQUESTS] Status {status}")

            if status != 200:
                return [], status

            if "Доступ ограничен" in response.text:
                logger.warning("Access restricted")
                return [], 403

            soup = BeautifulSoup(response.text, "lxml")
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

            logger.info(f"[REQUESTS] Found {len(items)} items")

            return items, 200

        except requests.exceptions.Timeout:
            return [], 408
        except Exception as e:
            logger.exception(f"[REQUESTS ERROR] {e}")
            return [], 500
