from playwright.async_api import async_playwright
from loguru import logger


class AvitoPlaywrightClient:
    """
    ASYNC Playwright клиент для Avito.
    """

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy

    async def get_html(self, url: str) -> str:
        logger.info(f"Playwright: открываю {url}")
        logger.info(f"Playwright: прокси = {self.proxy}")

        async with async_playwright() as p:

            launch_args = {
                "headless": False,  # 🚀 ВАЖНО
                "args": [
                    "--disable-blink-features=AutomationControlled",
                ],
            }

            # 🔥 Если есть прокси — подключаем
            if self.proxy:
                # формат: ip:port:login:pass
                parts = self.proxy.split(":")
                if len(parts) == 4:
                    ip, port, login, password = parts
                    launch_args["proxy"] = {
                        "server": f"http://{ip}:{port}",
                        "username": login,
                        "password": password,
                    }
                elif len(parts) == 2:
                    ip, port = parts
                    launch_args["proxy"] = {
                        "server": f"http://{ip}:{port}",
                    }

            browser = await p.chromium.launch(**launch_args)

            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
            )

            page = await context.new_page()

            # 🚀 Убираем webdriver
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            await page.goto(url, timeout=60000)

            # Ждём реальный рендер
            await page.wait_for_timeout(5000)

            html = await page.content()

            await browser.close()

            logger.info("Playwright: HTML получен")
            return html
