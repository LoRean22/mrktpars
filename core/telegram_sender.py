import httpx

BOT_TOKEN = "8529435887:AAHjrDxKJ8CBBtagAWb4zZ7mtJaiEfTc5S0"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(tg_id: int, text: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": tg_id,
                "text": text,
                "parse_mode": "HTML"
            }
        )

        print("TG STATUS:", r.status_code)
        print("TG RESPONSE:", r.text)





