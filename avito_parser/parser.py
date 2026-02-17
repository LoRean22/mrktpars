import requests
import random
import time
import re
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
from loguru import logger

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

# 🔥 Кэш сессий (чтобы прокси не создавались каждый раз)
_sessions = {}


def build_proxy_url(proxy_raw: str | None):
    """
    Конвертирует формат:
    ip:port:login:password
    в:
    http://login:password@ip:port
    """
    if not proxy_raw:
        return None

    parts = proxy_raw.split(":")

    if len(parts) == 4:
        ip, port, login, password = parts
        return f"http://{login}:{password}@{ip}:{port}"

    if len(parts) == 2:
        ip, port = parts
        return f"http://{ip}:{port}"

    raise ValueError("Неверный формат прокси")


def get_session(proxy_raw: str | None):
    key = proxy_raw or "direct"

    if key not in _sessions:
        logger.info(f"[SESSION] Creating new session for {key}")

        session = requests.Session()
        session.headers.update(HEADERS)

        proxy_url = build_proxy_url(proxy_raw)

        if proxy_url:
            session.proxies.update({
                "http": proxy_url,
                "https": proxy_url
            })

        _sessions[key] = session

    return _sessions[key]


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.proxy_raw = proxy
        self.session = get_session(proxy)

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    def parse_once(self, url: str) -> List[AvitoItem]:

        try:
            time.sleep(random.uniform(0.8, 1.5))

            url = self.clean_url(url)

            response = self.session.get(url, timeout=20)

            logger.info(f"[REQUESTS] Status {response.status_code}")

            if response.status_code == 429:
                logger.warning("[REQUESTS] 429 BAN")
                return []

            if response.status_code != 200:
                return []

            if "Доступ ограничен" in response.text:
                logger.warning("[REQUESTS] Access restricted")
                return []

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

            return items

        except Exception as e:
            logger.error(f"[PARSER ERROR] {e}")
            return []
