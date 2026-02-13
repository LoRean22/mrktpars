import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message, WebAppInfo
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8529435887:AAHjrDxKJ8CBBtagAWb4zZ7mtJaiEfTc5S0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть MRKTPARS",
                    web_app=WebAppInfo(url="https://lorean22.github.io/")
                )
            ]
        ]
    )

    await message.answer(
        "Добро пожаловать в MRKTPARS 🔥",
        reply_markup=keyboard
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
