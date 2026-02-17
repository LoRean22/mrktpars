import requests
import random
import time
from typing import List
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse, parse_qs, urlencode
import re

from avito_parser.models import AvitoItem

MAX_ITEMS = 20

HEADERS = {
    "User-Agent": random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    ]),
    "Accept-Language": "ru-RU,ru;q=0.9",
}


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        if proxy:
            parts = proxy.split(":")

            if len(parts) == 4:
                ip, port, login, password = parts
                proxy_url = f"http://{login}:{password}@{ip}:{port}"
            elif len(parts) == 2:
                ip, port = parts
                proxy_url = f"http://{ip}:{port}"
            else:
                raise ValueError("Неверный формат прокси")

            self.session.proxies.update({
                "http": proxy_url,
                "https": proxy_url,
            })

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    def parse_once(self, url: str) -> List[AvitoItem]:

        logger.info(f"Parser: начинаю парсинг {url}")

        time.sleep(random.uniform(0.8, 1.5))

        url = self.clean_url(url)

        response = self.session.get(url, timeout=20)

        if response.status_code != 200:
            logger.warning(f"Статус {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select('[data-marker="item"]')[:MAX_ITEMS]

        items: List[AvitoItem] = []

        for card in cards:
            try:
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
                short_url = f"https://avito.ru/{item_id}"

                title = link.get_text(strip=True)

                price_tag = card.select_one('[data-marker="item-price"]')
                price = 0
                if price_tag:
                    digits = "".join(c for c in price_tag.text if c.isdigit())
                    if digits:
                        price = int(digits)

                # -------- ДОПОЛНИТЕЛЬНЫЙ ЗАПРОС В КАРТОЧКУ --------
                seller_name = None
                seller_type = None
                seller_since = None
                image_url = None

                detail_resp = self.session.get(href, timeout=20)
                if detail_resp.status_code == 200:
                    detail_soup = BeautifulSoup(detail_resp.text, "lxml")

                    # имя продавца
                    seller_block = detail_soup.select_one('[data-marker="seller-info/name"]')
                    if seller_block:
                        seller_name = seller_block.get_text(strip=True)

                    # тип продавца
                    seller_type_block = detail_soup.select_one('[data-marker="seller-info/type"]')
                    if seller_type_block:
                        seller_type = seller_type_block.get_text(strip=True)

                    # на авито с ...
                    seller_since_block = detail_soup.select_one('[data-marker="seller-info/start-date"]')
                    if seller_since_block:
                        seller_since = seller_since_block.get_text(strip=True)

                    # главное фото
                    img = detail_soup.select_one('img[data-marker="image/image"]')
                    if img:
                        image_url = img.get("src")

                items.append(
                    AvitoItem(
                        id=item_id,
                        title=title,
                        price=price,
                        url=short_url,
                        image_url=image_url,
                        seller_name=seller_name,
                        seller_type=seller_type,
                        seller_since=seller_since
                    )
                )

            except Exception as e:
                logger.exception(f"Ошибка карточки: {e}")

        return items
