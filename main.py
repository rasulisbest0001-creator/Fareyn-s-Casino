from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = "ВСТАВЬ_СЮДА_ТОКЕН"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    print("ПОЛУЧИЛ /start")
    await message.answer("Работает ✅")

if __name__ == "__main__":
    print("БОТ ЗАПУЩЕН")
    executor.start_polling(dp, skip_updates=True)
