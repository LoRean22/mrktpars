import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(tg_id: int, text: str, image_url: str | None = None):

    if image_url:
        r = requests.post(
            f"{BASE_URL}/sendPhoto",
            json={
                "chat_id": tg_id,
                "photo": image_url,
                "caption": text
            },
            timeout=15
        )
    else:
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": tg_id,
                "text": text
            },
            timeout=10
        )

    print("TG STATUS:", r.status_code)
    print("TG RESPONSE:", r.text)

    return r.status_code


