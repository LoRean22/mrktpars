import requests

BOT_TOKEN = "8529435887:AAHjrDxKJ8CBBtagAWb4zZ7mtJaiEfTc5S0"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(tg_id: int, text: str):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": tg_id,
                "text": text
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram send error:", e)


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
