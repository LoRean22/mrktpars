from playwright.async_api import async_playwright
from loguru import logger

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts = {}

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        logger.info("Playwright browser started")

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright stopped")

    async def get_context(self, tg_id: int, proxy: str | None = None):
        if tg_id in self.contexts:
            return self.contexts[tg_id]

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
            locale="ru-RU",
            proxy=proxy_config
        )

        self.contexts[tg_id] = context
        return context



browser_manager = BrowserManager()
