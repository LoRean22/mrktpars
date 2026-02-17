import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(tg_id: int, text: str):
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
