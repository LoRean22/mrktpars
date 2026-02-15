import requests
from loguru import logger


class AvitoClient:
    """
    HTTP-клиент для Avito.
    Имитирует обычный браузер.
    """

    def __init__(self, proxy: str | None = None):
        self.session = requests.Session()

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        self.session.headers.update(self.headers)

        if proxy:
            self.session.proxies.update(
                {
                    "http": proxy,
                    "https": proxy,
                }
            )
            logger.info(f"AvitoClient: используется прокси {proxy}")

    def get(self, url: str) -> str:
        """
        Делает GET-запрос к Avito и возвращает HTML
        """

        logger.info(f"AvitoClient: GET {url}")

        response = self.session.get(url, timeout=20)

        if response.status_code != 200:
            raise RuntimeError(
                f"AvitoClient: статус {response.status_code}"
            )

        return response.text
