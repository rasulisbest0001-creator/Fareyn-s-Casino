import os
import json
import random

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# TOKEN
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DATA_FILE = "data.json"


# ---------- DATA ----------
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def user(user_id):
    data = load()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"balance": 5000, "bonus": False}
        save(data)

    return data[uid]


def set_balance(user_id, amount):
    data = load()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"balance": 5000, "bonus": False}

    data[uid]["balance"] += amount
    save(data)


# ---------- STATES ----------
class Game(StatesGroup):
    roulette = State()


# ---------- MENU ----------
kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb.add("💰 Баланс", "🎲 Рулетка")
kb.add("🏆 Бонус", "❌ Отмена")


# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user(message.from_user.id)
    await message.answer(
        "🎰 Казино бот\nВыбери действие:",
        reply_markup=kb
    )


# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(message: types.Message):
    u = user(message.from_user.id)
    await message.answer(f"💰 Баланс: {u['balance']} FRN")


# ---------- BONUS ----------
@dp.message_handler(lambda m: m.text == "🏆 Бонус")
async def bonus(message: types.Message):
    data = load()
    uid = str(message.from_user.id)
    u = data[uid]

    if u["bonus"]:
        await message.answer("❌ Бонус уже получен")
    else:
        u["balance"] += 10000
        u["bonus"] = True
        save(data)
        await message.answer("🎁 +10000 FRN бонус!")


# ---------- ROULETTE START ----------
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roulette_start(message: types.Message):
    await Game.roulette.set()
    await message.answer("🎲 Введи: число (0-36) и ставку\nПример: 17 100")


# ---------- ROULETTE LOGIC ----------
@dp.message_handler(state=Game.roulette)
async def roulette_play(message: types.Message, state: FSMContext):
    try:
        number, bet = map(int, message.text.split())

        if not (0 <= number <= 36):
            return await message.answer("❌ Число 0-36")

        if bet <= 0:
            return await message.answer("❌ Ставка > 0")

        uid = str(message.from_user.id)
        data = load()

        if data[uid]["balance"] < bet:
            return await message.answer("❌ Нет денег")

        win = random.randint(0, 36)

        if win == number:
            reward = bet * 35
            data[uid]["balance"] += reward
            text = f"🎉 WIN!\nВыпало: {win}\n+{reward} FRN"
        else:
            data[uid]["balance"] -= bet
            text = f"💔 LOSE\nВыпало: {win}\n-{bet} FRN"

        save(data)

        await message.answer(text, reply_markup=kb)
        await state.finish()

    except:
        await message.answer("❌ Формат: 17 100")


# ---------- CANCEL ----------
@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("↩️ Отменено", reply_markup=kb)


# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
