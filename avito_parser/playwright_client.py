from playwright.async_api import async_playwright
from loguru import logger


class AvitoPlaywrightClient:

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy

    async def get_html(self, url: str) -> str:
        logger.info(f"Playwright: открываю {url}")
        logger.info(f"Playwright: прокси = {self.proxy}")

        async with async_playwright() as p:

            launch_args = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            }

            # 🔥 ЕСЛИ есть прокси — правильно передаем
            if self.proxy:
                parts = self.proxy.split(":")

                if len(parts) == 4:
                    host, port, login, password = parts
                    launch_args["proxy"] = {
                        "server": f"http://{host}:{port}",
                        "username": login,
                        "password": password,
                    }
                else:
                    host, port = parts
                    launch_args["proxy"] = {
                        "server": f"http://{host}:{port}"
                    }

            browser = await p.chromium.launch(**launch_args)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
            )

            page = await context.new_page()

            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            await page.goto(url, timeout=30000)

            await page.wait_for_timeout(5000)

            html = await page.content()

            # 🔥 Диагностика
            with open("debug_avito.html", "w", encoding="utf-8") as f:
                f.write(html)

            await browser.close()

            logger.info("Playwright: HTML получен")
            return html
