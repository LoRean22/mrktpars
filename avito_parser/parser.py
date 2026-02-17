import requests
import random
import time
from typing import List
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse, parse_qs, urlencode
import re

from avito_parser.models import AvitoItem

MAX_ITEMS_LIMIT = 7  # максимум который может дойти
MIN_ITEMS_LIMIT = 4  # минимум финального лимита

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
]


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy
        self.session = requests.Session()

        # Реалистичные headers
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.avito.ru/",
        })

        # Sticky proxy
        if proxy:
            logger.info(f"Parser: использую прокси {proxy}")
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

        # динамический лимит карточек
        self.dynamic_limit = 1
        self.max_limit = random.randint(MIN_ITEMS_LIMIT, MAX_ITEMS_LIMIT)

    # -------------------------
    # ПРОГРЕВ
    # -------------------------

    def warmup(self, url: str):
        try:
            logger.info("Parser: прогрев IP")

            # 1. Главная
            self.session.get("https://www.avito.ru", timeout=15)
            time.sleep(random.uniform(1.0, 2.0))

            # 2. Регион
            parsed = urlparse(url)
            region_url = f"{parsed.scheme}://{parsed.netloc}"
            self.session.get(region_url, timeout=15)
            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            logger.warning(f"WARMUP ERROR: {e}")

    # -------------------------

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    # -------------------------

    def parse_once(self, url: str) -> List[AvitoItem]:

        # стартовая задержка
        time.sleep(random.uniform(2.0, 4.0))

        url = self.clean_url(url)

        # если первый запуск — прогреваем
        if self.dynamic_limit == 1:
            self.warmup(url)

        logger.info(f"[REQUESTS] Парсинг {url}")

        try:
            response = self.session.get(url, timeout=20)
        except Exception as e:
            logger.warning(f"REQUEST ERROR: {e}")
            return []

        logger.info(f"[REQUESTS] Status {response.status_code}")

        if response.status_code == 429:
            logger.warning("IP забанен (429)")
            return []

        if response.status_code != 200:
            return []

        if "Доступ ограничен" in response.text:
            logger.warning("Avito ограничил доступ")
            return []

        soup = BeautifulSoup(response.text, "lxml")

        cards = soup.select('[data-marker="item"]')

        # увеличиваем лимит постепенно
        cards = cards[:self.dynamic_limit]

        if self.dynamic_limit < self.max_limit:
            self.dynamic_limit += 1

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

                # изображение
                image_tag = card.select_one("img")
                image_url = None
                if image_tag:
                    image_url = image_tag.get("src")

                items.append(
                    AvitoItem(
                        id=item_id,
                        title=title,
                        price=price,
                        url=short_url,
                        image_url=image_url
                    )
                )

            except Exception as e:
                logger.exception(f"Ошибка карточки: {e}")

        return items
