import os
import json
import random

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# ======================
# 🔑 TOKEN (ВАЖНО)
# ======================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ======================
# 💾 DATABASE
# ======================
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"balance": 5000}
        save_data(data)

    return data

# ======================
# 🎮 STATES
# ======================
class Game(StatesGroup):
    roulette = State()

# ======================
# 🎛 KEYBOARD
# ======================
kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb.add("💰 Баланс", "🎲 Рулетка")

# ======================
# START
# ======================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    get_user(message.from_user.id)

    await message.answer(
        "🎰 Казино запущено!\nВыбери действие:",
        reply_markup=kb
    )

# ======================
# BALANCE
# ======================
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(message: types.Message):
    data = get_user(message.from_user.id)
    bal = data[str(message.from_user.id)]["balance"]

    await message.answer(f"💰 Баланс: {bal} FRN")

# ======================
# ROULETTE START
# ======================
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roulette_start(message: types.Message):
    await Game.roulette.set()
    await message.answer("🎲 Введи: число и ставку\nПример: 17 100")

# ======================
# ROULETTE LOGIC
# ======================
@dp.message_handler(state=Game.roulette)
async def roulette_play(message: types.Message, state: FSMContext):
    try:
        number, bet = map(int, message.text.split())

        if not (0 <= number <= 36):
            return await message.answer("❌ Число 0-36")

        if bet <= 0:
            return await message.answer("❌ Ставка > 0")

        data = get_user(message.from_user.id)
        uid = str(message.from_user.id)

        if data[uid]["balance"] < bet:
            return await message.answer("❌ Нет денег")

        win = random.randint(0, 36)

        if win == number:
            reward = bet * 35
            data[uid]["balance"] += reward
            text = f"🎉 WIN! Выпало {win}\n+{reward} FRN"
        else:
            data[uid]["balance"] -= bet
            text = f"💀 Lose! Выпало {win}\n-{bet} FRN"

        save_data(data)

        await message.answer(text, reply_markup=kb)
        await state.finish()

    except:
        await message.answer("❌ Формат: число ставка")

# ======================
# CANCEL (если нужно)
# ======================
@dp.message_handler(commands=["cancel"], state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Отменено", reply_markup=kb)

# ======================
# START BOT
# ======================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
