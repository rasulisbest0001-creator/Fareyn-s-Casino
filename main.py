import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise Exception("API_TOKEN not set in Railway Variables")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Bot works ✅")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
