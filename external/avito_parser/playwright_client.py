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

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,   # 🔥 ВАЖНО
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
            )

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

            try:
                await page.wait_for_selector(
                    '[data-marker="item"], div[data-item-id]',
                    timeout=10000
                )
            except Exception:
                logger.warning("Карточки не появились, продолжаем")

            await page.wait_for_timeout(2000)

            html = await page.content()

            await browser.close()

            logger.info("Playwright: HTML получен")
            return html
