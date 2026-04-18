import os
import json
import random
import time
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

ADMIN_ID = 123456789  # <-- ВСТАВЬ СВОЙ ID

DATA_FILE = "data.json"

START_BALANCE = 5000
BONUS_AMOUNT = 5555
HOURLY_BONUS = 2500
BONUS_COOLDOWN = 5400

cooldowns = {}

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

def user(uid):
    data = load()
    uid = str(uid)

    if uid not in data:
        data[uid] = {
            "balance": START_BALANCE,
            "bonus": False,
            "last_bonus": 0
        }
        save(data)

    return data[uid]

def update(uid, amount):
    data = load()
    uid = str(uid)

    data[uid]["balance"] += amount
    if data[uid]["balance"] < 0:
        data[uid]["balance"] = 0

    save(data)

# ---------- ANTI SPAM ----------
def check_cd(uid):
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < 1:
        return False
    cooldowns[uid] = now
    return True

# ---------- MENU ----------
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🎲 Рулетка")
    kb.add("💣 Мины", "🎁 Бонус")
    kb.add("⏱ Бонус")
    return kb

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    user(m.from_user.id)
    await m.answer("🔥 Лучший казино бот", reply_markup=menu())

# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(m: types.Message):
    if not check_cd(m.from_user.id): return
    u = user(m.from_user.id)
    await m.answer(f"💰 {u['balance']} FRN")

# ---------- BONUS ----------
@dp.message_handler(lambda m: m.text == "🎁 Бонус")
async def bonus(m: types.Message):
    data = load()
    uid = str(m.from_user.id)

    if data[uid]["bonus"]:
        return await m.answer("❌ Уже взял")

    data[uid]["bonus"] = True
    data[uid]["balance"] += BONUS_AMOUNT
    save(data)

    await m.answer("🎁 +5555 FRN")

# ---------- HOURLY ----------
@dp.message_handler(lambda m: m.text == "⏱ Бонус")
async def hourly(m: types.Message):
    data = load()
    uid = str(m.from_user.id)

    now = time.time()

    if now - data[uid]["last_bonus"] < BONUS_COOLDOWN:
        return await m.answer("⏳ Подожди")

    data[uid]["last_bonus"] = now
    data[uid]["balance"] += HOURLY_BONUS
    save(data)

    await m.answer("💸 +2500")

# ---------- ROULETTE ----------
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roul(m: types.Message):
    await m.answer("Введите: число ставка")

@dp.message_handler(lambda m: m.text and " " in m.text)
async def roul_play(m: types.Message):
    if not check_cd(m.from_user.id): return

    try:
        num, bet = map(int, m.text.split())

        u = user(m.from_user.id)
        if u["balance"] < bet or bet <= 0:
            return

        roll = random.randint(0, 36)

        update(m.from_user.id, -bet)

        if num == roll:
            win = bet * 30
            update(m.from_user.id, win)
            await m.answer(f"🎉 WIN {win} | {roll}")
        else:
            await m.answer(f"💀 LOSE | {roll}")

    except:
        pass

# ---------- MINES ----------
games = {}

@dp.message_handler(lambda m: m.text == "💣 Мины")
async def mines(m: types.Message):
    await m.answer("Введи ставку")

@dp.message_handler()
async def mines_play(m: types.Message):
    uid = m.from_user.id

    if m.text.isdigit():
        bet = int(m.text)
        u = user(uid)

        if u["balance"] < bet:
            return

        update(uid, -bet)

        games[uid] = {
            "bet": bet,
            "bombs": random.sample(range(20), 5),
            "multi": 1.0
        }

        return await m.answer("Игра началась")

    if uid in games:
        game = games[uid]

        if m.text == "cash":
            win = int(game["bet"] * game["multi"])
            update(uid, win)
            del games[uid]
            return await m.answer(f"💰 {win}")

        try:
            cell = int(m.text)

            if cell in game["bombs"]:
                del games[uid]
                return await m.answer("💀 Бомба")

            game["multi"] *= 1.4
            await m.answer(f"x{game['multi']:.2f}")

        except:
            pass

# ---------- ADMIN ----------
@dp.message_handler(commands=["add"])
async def add(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    amount = int(m.get_args())
    update(m.from_user.id, amount)
    await m.answer(f"+{amount}")

@dp.message_handler(commands=["give"])
async def give(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    uid, amount = m.get_args().split()
    update(int(uid), int(amount))
    await m.answer("выдано")

@dp.message_handler(commands=["set"])
async def setb(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    uid, amount = m.get_args().split()
    data = load()
    data[str(uid)]["balance"] = int(amount)
    save(data)
    await m.answer("установлено")

@dp.message_handler(commands=["take"])
async def take(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    uid, amount = m.get_args().split()
    update(int(uid), -int(amount))
    await m.answer("забрано")

# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
