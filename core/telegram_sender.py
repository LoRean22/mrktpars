import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(tg_id: int, text: str, image_url: str | None = None):
    endpoint = "sendPhoto" if image_url else "sendMessage"
    payload = {
        "chat_id": tg_id,
        "caption" if image_url else "text": text
    }

    if image_url:
        payload["photo"] = image_url

    r = requests.post(f"{BASE_URL}/{endpoint}", json=payload, timeout=15)

    print("TG STATUS:", r.status_code)
    print("TG RESPONSE:", r.text)

    return r.status_code
