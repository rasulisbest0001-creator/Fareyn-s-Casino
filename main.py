import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "ТВОЙ_ТОКЕН_ИЗ_TXT"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ==== БАЗА (временная, потом заменишь на БД) ====
users = {}

# ==== КНОПКИ ====
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("👤 Профиль"))
menu.add(KeyboardButton("🎮 Игры"))

# ==== СТАРТ ====
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            "balance": 1000
        }

    await message.answer(
        "🎰 Добро пожаловать в Fareyn’s Casino!\n\n"
        "Используй меню ниже 👇",
        reply_markup=menu
    )

# ==== ПРОФИЛЬ ====
@dp.message_handler(lambda message: message.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id

    balance = users.get(user_id, {}).get("balance", 0)

    await message.answer(
        f"👤 ID: {user_id}\n"
        f"💰 Баланс: {balance}"
    )

# ==== ИГРЫ ====
@dp.message_handler(lambda message: message.text == "🎮 Игры")
async def games(message: types.Message):
    await message.answer(
        "🎮 Доступные игры:\n"
        "🎯 Рулетка (в разработке)\n\n"
        "Скоро добавлю ставки 😉"
    )

# ==== ПРОСТАЯ СТАВКА (ПРИМЕР) ====
@dp.message_handler()
async def handle_bet(message: types.Message):
    user_id = message.from_user.id
    text = message.text.split()

    if len(text) < 2:
        return

    try:
        amount = int(text[0])
        bet = text[1]

        if user_id not in users:
            users[user_id] = {"balance": 1000}

        if users[user_id]["balance"] < amount:
            await message.answer("❌ Недостаточно средств")
            return

        users[user_id]["balance"] -= amount

        await message.answer(
            f"✅ Ставка {amount} на {bet} принята"
        )

    except:
        pass

# ==== ЗАПУСК ====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
