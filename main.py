import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise Exception("API_TOKEN НЕ НАЙДЕН В VARIABLES")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("бот работает ✅")

if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
