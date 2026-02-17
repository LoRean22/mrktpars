import aiohttp
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(tg_id: int, text: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": tg_id,
                    "text": text
                }
            ) as response:
                return response.status
        except Exception:
            return 500
