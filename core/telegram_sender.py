import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Явно указываем путь
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(f"BOT_TOKEN not found in {env_path}")

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
