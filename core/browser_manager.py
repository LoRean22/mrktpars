from playwright.async_api import async_playwright
from loguru import logger
import random


class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )


        logger.info("Playwright browser started")

    async def stop(self):
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"Browser close error (ignored): {e}")

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Playwright stop error (ignored): {e}")

        logger.info("Playwright browser stopped")


    async def new_context(self, proxy: str | None = None):

        proxy_config = None

        if proxy:
            parts = proxy.split(":")
            if len(parts) == 4:
                ip, port, login, password = parts
                proxy_config = {
                    "server": f"http://{ip}:{port}",
                    "username": login,
                    "password": password
                }
            elif len(parts) == 2:
                ip, port = parts
                proxy_config = {
                    "server": f"http://{ip}:{port}"
                }

        context = await self.browser.new_context(
            proxy=proxy_config,
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            ]),
            viewport={"width": 1280, "height": 900}
        )

        return context


browser_manager = BrowserManager()
