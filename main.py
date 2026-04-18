import os
import json
import random
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found")

GIF = "CgACAgQAAxkBAAFHdp1p4vZvtNFn0-k9ncI_X2ZBgAwvTAAC6wYAAjJmPFDhjlHaIPdqszsE"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DATA_FILE = "data.json"
START_BALANCE = 5000

# ---------------- DATA ----------------
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
        data[uid] = {"balance": START_BALANCE, "bonus": False}
        save_data(data)

    return data[uid]

def update_balance(user_id, amount):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"balance": START_BALANCE, "bonus": False}

    data[uid]["balance"] += amount
    save_data(data)

# ---------------- STATES ----------------
class Game(StatesGroup):
    roulette = State()
    mines = State()

# ---------------- MENU ----------------
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🎲 Рулетка")
    kb.add("💣 Мины", "🏆 Бонус")
    kb.add("❌ Отмена")
    return kb

# ---------------- START ----------------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer("🎮 Казино запущено", reply_markup=menu())

# ---------------- BALANCE ----------------
@dp.message_handler(lambda m: m.text == "💰 Баланс", state="*")
async def balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💰 Баланс: {user['balance']} FRN")

# ---------------- CANCEL ----------------
@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Отменено", reply_markup=menu())

# ---------------- ROULETTE ----------------
@dp.message_handler(lambda m: m.text == "🎲 Рулетка", state="*")
async def roulette_start(message: types.Message):
    await Game.roulette.set()
    await message.answer("🎲 Введите: число ставка\nПример: 17 100")

@dp.message_handler(state=Game.roulette)
async def roulette_play(message: types.Message, state: FSMContext):
    try:
        number, bet = map(int, message.text.split())

        if number < 0 or number > 36 or bet <= 0:
            return await message.answer("❌ ошибка")

        user = get_user(message.from_user.id)

        if user["balance"] < bet:
            return await message.answer("❌ нет денег")

        win_number = random.randint(0, 36)

        if number == win_number:
            win = bet * 35
            update_balance(message.from_user.id, win)
            text = f"🎉 WIN {win}\n🎲 {win_number}"
        else:
            update_balance(message.from_user.id, -bet)
            text = f"💀 LOSE\n🎲 {win_number}"

        await bot.send_animation(message.chat.id, GIF)
        await message.answer(text, reply_markup=menu())

        await state.finish()

    except:
        await message.answer("❌ формат: число ставка")

# ---------------- MINES ----------------
@dp.message_handler(lambda m: m.text == "💣 Мины", state="*")
async def mines_start(message: types.Message):
    await Game.mines.set()
    await message.answer("💣 Введи ставку")

@dp.message_handler(state=Game.mines)
async def mines_setup(message: types.Message, state: FSMContext):
    try:
        bet = int(message.text)

        user = get_user(message.from_user.id)
        if user["balance"] < bet:
            return await message.answer("❌ нет денег")

        bombs = random.sample(range(20), 7)

        await state.update_data(
            bet=bet,
            bombs=bombs,
            opened=[],
            multiplier=1.0
        )

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(20):
            kb.insert(str(i))
        kb.add("💰 cash")

        await message.answer("💣 игра началась (0–19, 7 бомб)", reply_markup=kb)

    except:
        await message.answer("❌ введи число")

@dp.message_handler(state=Game.mines)
async def mines_play(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id

    # CASH OUT
    if message.text == "💰 cash":
        reward = int(data["bet"] * data["multiplier"])
        update_balance(uid, reward)

        await message.answer(
            f"💰 CASHOUT x{data['multiplier']:.2f}\n"
            f"💸 +{reward}",
            reply_markup=menu()
        )
        return await state.finish()

    try:
        cell = int(message.text)

        if cell < 0 or cell > 19:
            return await message.answer("❌ 0–19")

        if cell in data["opened"]:
            return await message.answer("⚠️ уже открыто")

        if cell in data["bombs"]:
            update_balance(uid, -data["bet"])
            await message.answer(
                f"💣 БОМБА!\n- {data['bet']} FRN",
                reply_markup=menu()
            )
            return await state.finish()

        opened = data["opened"]
        opened.append(cell)

        multiplier = round(data["multiplier"] * 1.35, 2)

        await state.update_data(opened=opened, multiplier=multiplier)

        await message.answer(f"✅ безопасно x{multiplier}")

    except:
        await message.answer("❌ ошибка")

# ---------------- BONUS ----------------
@dp.message_handler(lambda m: m.text == "🏆 Бонус", state="*")
async def bonus(message: types.Message):
    data = load_data()
    uid = str(message.from_user.id)

    if data.get(uid, {}).get("bonus"):
        return await message.answer("❌ уже забрал")

    data[uid]["balance"] += 10000
    data[uid]["bonus"] = True

    save_data(data)

    await message.answer("🎁 +10000 FRN")

# ---------------- UNKNOWN ----------------
@dp.message_handler()
async def unknown(message: types.Message):
    await message.answer("❓ неизвестно", reply_markup=menu())

# ---------------- START ----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
