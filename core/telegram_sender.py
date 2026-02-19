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
            r = requests.post(
                f"{BASE_URL}/sendPhoto",
                json={
                    "chat_id": tg_id,
                    "photo": image_url,
                    "caption": text,
                    "parse_mode": "HTML"
                },
                timeout=20
            )
        else:
            r = requests.post(
                f"{BASE_URL}/sendMessage",
                json={
                    "chat_id": tg_id,
                    "text": text,
                    "parse_mode": "HTML"
                },
                timeout=20
            )

        return r.status_code

    except Exception as e:
        print("TG SEND ERROR:", e)
        return 0
