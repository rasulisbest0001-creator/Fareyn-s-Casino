import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================= TOKEN =================

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= STORAGE =================

FILE = "data.json"

users = {}
games = {
    "bets": [],
    "mines": {},
    "joker": {}
}

# ================= UI =================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("💰 Баланс", "🎮 Игры")
menu.row("💣 Мины", "🃏 Джокер")
menu.row("🎲 Рулетка", "🏆 Бонус")

# ================= DATA =================

def load():
    global users
    try:
        users = json.load(open(FILE))
    except:
        users = {}

def save():
    json.dump(users, open(FILE), "w", indent=2)

def u(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"balance": 0, "bonus": False}
    return users[uid]

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    user = u(m.from_user.id)

    if user["balance"] == 0:
        user["balance"] = 5000

    save()

    await m.answer(
        "🎰 FAREYN CASINO\n\n"
        f"💰 Баланс: {user['balance']} FRN\n\n"
        "🎮 Игры:\n"
        "🎲 Рулетка — число + ставка\n"
        "💣 Мины — риск x1.3\n"
        "🃏 Джокер — x1.33\n\n"
        "🏆 /bonus — стартовый бонус",
        reply_markup=menu
    )

# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(m: types.Message):
    user = u(m.from_user.id)
    await m.answer(f"💰 Баланс: {user['balance']} FRN")

# ================= BONUS =================

@dp.message_handler(commands=["bonus"])
async def bonus(m: types.Message):
    user = u(m.from_user.id)

    if user["bonus"]:
        return await m.answer("❌ уже получено")

    user["bonus"] = True
    user["balance"] += 10000

    save()
    await m.answer("🎁 +10000 FRN")

# ================= ROULETTE =================

@dp.message_handler(lambda m: m.text and len(m.text.split()) == 2)
async def bet(m: types.Message):
    uid = m.from_user.id
    user = u(uid)

    try:
        num, amount = map(int, m.text.split())
    except:
        return

    if user["balance"] < amount:
        return await m.answer("❌ нет денег")

    user["balance"] -= amount
    games["bets"].append((uid, num, amount))

    save()
    await m.answer("🎲 ставка принята")

@dp.message_handler(commands=["go"])
async def go(m: types.Message):
    bets = games["bets"]
    if not bets:
        return await m.answer("❌ нет ставок")

    win = random.randint(0, 36)

    text = f"🎯 ВЫПАЛО: {win}\n\n"

    for uid, num, amount in bets:
        user = u(uid)

        try:
            name = (await bot.get_chat(uid)).first_name
        except:
            name = "Игрок"

        if num == win:
            prize = amount * 35
            user["balance"] += prize
            text += f"✅ {name} +{prize}\n"
        else:
            text += f"❌ {name} -{amount}\n"

    games["bets"] = []
    save()

    await m.answer(text)

# ================= MINES =================

@dp.message_handler(commands=["mines"])
async def mines(m: types.Message):
    uid = m.from_user.id
    user = u(uid)

    try:
        bet = int(m.get_args())
    except:
        return await m.answer("❌ /mines 100")

    if user["balance"] < bet:
        return await m.answer("❌ нет денег")

    user["balance"] -= bet

    games["mines"][uid] = {
        "bet": bet,
        "mult": 1.0,
        "bombs": set(random.sample(range(25), 7))
    }

    save()
    await m.answer("💣 игра началась\n/pick N или /cash")

@dp.message_handler(commands=["pick"])
async def pick(m: types.Message):
    uid = m.from_user.id
    g = games["mines"].get(uid)

    if not g:
        return

    try:
        x = int(m.get_args())
    except:
        return

    if x in g["bombs"]:
        games["mines"].pop(uid)
        return await m.answer("💥 LOSE")

    g["mult"] *= 1.3
    await m.answer(f"✨ x{g['mult']:.2f}")

@dp.message_handler(commands=["cash"])
async def cash(m: types.Message):
    uid = m.from_user.id
    g = games["mines"].pop(uid, None)

    if not g:
        return

    user = u(uid)
    win = int(g["bet"] * g["mult"])
    user["balance"] += win

    save()
    await m.answer(f"💰 +{win}")

# ================= JOKER =================

@dp.message_handler(commands=["joker"])
async def joker(m: types.Message):
    uid = m.from_user.id
    user = u(uid)

    try:
        bet = int(m.get_args())
    except:
        return await m.answer("❌ /joker 100")

    if user["balance"] < bet:
        return await m.answer("❌ нет денег")

    user["balance"] -= bet

    games["joker"][uid] = {"bet": bet, "mult": 1.0}

    save()
    await m.answer("🃏 /flip")

@dp.message_handler(commands=["flip"])
async def flip(m: types.Message):
    uid = m.from_user.id
    g = games["joker"].get(uid)

    if not g:
        return

    if random.randint(1, 100) < 30:
        games["joker"].pop(uid)
        return await m.answer("💀 LOSE")

    g["mult"] *= 1.33
    await m.answer(f"✨ x{g['mult']:.2f}")

@dp.message_handler(commands=["cashjoker"])
async def cashjoker(m: types.Message):
    uid = m.from_user.id
    g = games["joker"].pop(uid, None)

    if not g:
        return

    user = u(uid)
    win = int(g["bet"] * g["mult"])
    user["balance"] += win

    save()
    await m.answer(f"💰 +{win}")

# ================= RUN =================

if __name__ == "__main__":
    load()
    executor.start_polling(dp)
