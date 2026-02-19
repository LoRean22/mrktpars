import requests
import random
import os
import pickle
from typing import List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
import re

from avito_parser.models import AvitoItem


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
]

COOKIE_DIR = "core/session_storage"
os.makedirs(COOKIE_DIR, exist_ok=True)

FIXED_ITEMS_LIMIT = 4


class AvitoParser:

    def __init__(self, proxy: str | None = None):

        self.session = requests.Session()
        self.proxy = proxy

        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://www.avito.ru/",
        })

        if proxy:
            self._configure_proxy(proxy)

        proxy_name = proxy.replace(":", "_") if proxy else "no_proxy"
        self.cookie_file = os.path.join(COOKIE_DIR, f"{proxy_name}.pkl")
        self._load_cookies()

    # -------------------------

    def close(self):
        self.session.close()

    # -------------------------

    def _configure_proxy(self, proxy: str):
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
            "https": proxy_url,
        })

    # -------------------------

    def _load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "rb") as f:
                    self.session.cookies.update(pickle.load(f))
            except:
                pass

    def _save_cookies(self):
        try:
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.session.cookies, f)
        except:
            pass

    # -------------------------

    def clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["s"] = ["104"]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(query, doseq=True)}"

    # -------------------------

    def extract_ids(self, soup) -> List[Tuple[str, str]]:
        results = []
        cards = soup.select('[data-marker="item"]')[:FIXED_ITEMS_LIMIT]

        for card in cards:
            link = card.select_one('a[data-marker="item-title"]')
            if not link:
                continue

            href = link.get("href")
            if not href:
                continue

            if href.startswith("/"):
                href = "https://www.avito.ru" + href

            match = re.search(r'_(\d+)$', href.split("?")[0])
            if not match:
                continue

            results.append((match.group(1), href))

        return results

    # -------------------------

    def parse_full_item(self, item_id: str, href: str):

        try:
            r = self.session.get(href, timeout=20)

            if r.status_code == 429:
                return None

            if r.status_code != 200:
                return None

            soup = BeautifulSoup(r.text, "lxml")

            title_tag = soup.select_one("h1")
            title = title_tag.get_text(strip=True) if title_tag else "Без названия"

            price = 0
            price_tag = soup.select_one('[data-marker="item-price"]')
            if price_tag:
                digits = "".join(c for c in price_tag.text if c.isdigit())
                if digits:
                    price = int(digits)

            og_image = soup.select_one('meta[property="og:image"]')
            image_url = og_image.get("content") if og_image else None

            return AvitoItem(
                id=item_id,
                title=title,
                price=price,
                url=href,
                image_url=image_url
            )

        except:
            return None

    # -------------------------

    def parse_once(self, url: str):

        url = self.clean_url(url)

        try:
            r = self.session.get(url, timeout=20)
        except:
            return [], 0

        if r.status_code == 429:
            return [], 429

        if r.status_code != 200:
            return [], r.status_code

        if "Доступ ограничен" in r.text:
            return [], 403

        self._save_cookies()

        soup = BeautifulSoup(r.text, "lxml")
        id_list = self.extract_ids(soup)

        return id_list, 200
