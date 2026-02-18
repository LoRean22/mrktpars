import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(tg_id: int, text: str, image_url: str | None = None):
    try:
        if image_url:
            # Отправляем как ДОКУМЕНТ (без сжатия)
            r = requests.post(
                f"{BASE_URL}/sendDocument",
                data={
                    "chat_id": tg_id,
                    "caption": text
                },
                files={
                    # Telegram сам скачает файл по URL без сжатия
                    "document": (None, image_url)
                },
                timeout=20
            )
        else:
            r = requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": tg_id,
                    "text": text
                },
                timeout=15
            )

        print("TG STATUS:", r.status_code)
        print("TG RESPONSE:", r.text)

        return r.status_code

    except Exception as e:
        print("TELEGRAM ERROR:", e)
        return 0
