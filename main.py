import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("бот работает")

if __name__ == "__main__":
    executor.start_polling(dp)
