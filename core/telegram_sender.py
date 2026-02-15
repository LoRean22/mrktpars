from aiogram import Bot
import asyncio

BOT_TOKEN = "8529435887:AAHjrDxKJ8CBBtagAWb4zZ7mtJaiEfTc5S0"

bot = Bot(token=BOT_TOKEN)


async def send_message(tg_id: int, text: str):
    await bot.send_message(tg_id, text)
