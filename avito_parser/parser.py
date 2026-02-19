import requests
import random
import time
import os
import pickle
from typing import List
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse, parse_qs, urlencode
import re

from avito_parser.models import AvitoItem

FIXED_ITEMS_LIMIT = 4

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
]

COOKIE_DIR = "core/session_storage"
os.makedirs(COOKIE_DIR, exist_ok=True)


class AvitoParser:

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.avito.ru/",
        })

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

        proxy_name = proxy.replace(":", "_") if proxy else "no_proxy"
        self.cookie_file = os.path.join(COOKIE_DIR, f"{proxy_name}.pkl")

        self.load_cookies()

    # ------------------------------------------------

    def load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "rb") as f:
                    self.session.cookies.update(pickle.load(f))
                logger.info("Cookies loaded")
            except:
                pass

    def save_cookies(self):
        try:
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.session.cookies, f)
        except:
            pass

    # ------------------------------------------------

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    # ------------------------------------------------
    # 🔹 Получаем карточки с страницы поиска
    # ------------------------------------------------

    def extract_cards(self, soup) -> List[dict]:
        results = []

        cards = soup.select('[data-marker="item"]')[:FIXED_ITEMS_LIMIT]

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
                title = link.get_text(strip=True)

                # 🔥 Цена берём только со страницы поиска
                price = 0
                price_tag = card.select_one('[data-marker="item-price"]')
                if price_tag:
                    digits = "".join(c for c in price_tag.get_text() if c.isdigit())
                    if digits:
                        price = int(digits)

                results.append({
                    "id": item_id,
                    "href": href,
                    "title": title,
                    "price": price
                })

            except Exception as e:
                logger.warning(f"Card parse error: {e}")
                continue

        return results

    # ------------------------------------------------
    # 🔹 Полный парсинг (ТОЛЬКО для картинки)
    # ------------------------------------------------

    def parse_full_item(self, item_id: str, href: str) -> AvitoItem | None:
        try:
            r = self.session.get(href, timeout=20)
            if r.status_code != 200:
                return None

            soup = BeautifulSoup(r.text, "lxml")

            # IMAGE
            og_image = soup.select_one('meta[property="og:image"]')
            image_url = og_image.get("content") if og_image else None

            short_url = f"https://avito.ru/{item_id}"

            return AvitoItem(
                id=item_id,
                title="",
                price=0,
                url=short_url,
                image_url=image_url
            )

        except Exception as e:
            logger.warning(f"FULL ITEM ERROR: {e}")
            return None

    # ------------------------------------------------
    # 🔹 Основной заход
    # ------------------------------------------------

    def parse_once(self, url: str):

        time.sleep(random.uniform(2.0, 4.0))
        url = self.clean_url(url)

        logger.info(f"[REQUESTS] Парсинг {url}")

        try:
            response = self.session.get(url, timeout=20)
        except Exception as e:
            logger.warning(f"REQUEST ERROR: {e}")
            return [], 0

        status = response.status_code
        logger.info(f"[REQUESTS] Status {status}")

        if status == 429:
            logger.warning("IP забанен (429)")
            return [], 429

        if status == 403:
            logger.warning("403 Forbidden")
            return [], 403

        if status != 200:
            logger.warning(f"Unexpected status {status}")
            return [], status

        if "Доступ ограничен" in response.text:
            logger.warning("Avito ограничил доступ")
            return [], 403

        self.save_cookies()

        soup = BeautifulSoup(response.text, "lxml")
        cards = self.extract_cards(soup)

        logger.info(f"[REQUESTS] Найдено карточек: {len(cards)}")

        return cards, 200
