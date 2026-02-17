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

    async def get_context(self, tg_id: int):
        if tg_id in self.contexts:
            return self.contexts[tg_id]

        context = await self.browser.new_context(
            user_agent=None,  # пусть Chromium сам выберет
            locale="ru-RU"
        )

        self.contexts[tg_id] = context
        return context


browser_manager = BrowserManager()
