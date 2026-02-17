import aiohttp
import os
from loguru import logger

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(tg_id: int, text: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": tg_id,
                    "text": text
                }
            ) as response:

                logger.info(f"[TELEGRAM] Sent to {tg_id} → status {response.status}")
                return response.status

    except Exception as e:
        logger.exception(f"[TELEGRAM] Error sending message: {e}")
        return 500
