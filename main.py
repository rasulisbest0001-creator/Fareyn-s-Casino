import os
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users.json"
users = {}


# ================= STORAGE =================

def load():
    global users
    try:
        with open(DATA_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}


def save():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "balance": 0,
            "best": False
        }
    return users[uid]


# ================= START =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    u = get_user(msg.from_user.id)

    if u["balance"] == 0:
        u["balance"] += 5000

    save()
    await msg.answer(f"🎰 Добро\n💰 Баланс: {u['balance']} FRN")


# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "б")
async def bal(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 {u['balance']} FRN")


# ================= SAFE COMMANDS =================

@dp.message_handler(commands=["fareyntop"])
async def fareyn(msg: types.Message):
    u = get_user(msg.from_user.id)
    u["balance"] += 1231231
    save()
    await msg.answer("🔥 +1231231 FRN")


@dp.message_handler(commands=["bestbot"])
async def best(msg: types.Message):
    u = get_user(msg.from_user.id)

    if u["best"]:
        return await msg.answer("❌ уже получено")

    u["balance"] += 5555
    u["best"] = True
    save()

    await msg.answer("🏆 +5555 FRN")


# ================= SIMPLE ROULETTE =================

bets = []

@dp.message_handler(lambda m: m.text and m.text[0].isdigit())
async def bet(msg: types.Message):
    u = get_user(msg.from_user.id)

    parts = msg.text.split()
    amount = int(parts[0])

    if u["balance"] < amount:
        return await msg.answer("❌ нет денег")

    u["balance"] -= amount

    for x in parts[1:]:
        bets.append((msg.from_user.id, amount, x))

    save()
    await msg.answer("🎲 ставка принята")


@dp.message_handler(commands=["go"])
async def go(msg: types.Message):
    global bets

    if not bets:
        return await msg.answer("❌ нет ставок")

    num = random.randint(0, 36)

    text = f"🎯 Выпало: {num}\n\n"

    for uid, amount, bet in bets:
        u = get_user(uid)

        win = False
        mult = 0

        if bet == str(num):
            win = True
            mult = 35

        if win:
            win_money = amount * mult
            u["balance"] += win_money
            text += f"✅ {uid} +{win_money}\n"
        else:
            text += f"❌ {uid}\n"

    bets = []
    save()

    await msg.answer(text)


# ================= RUN =================

if __name__ == "__main__":
    load()
    executor.start_polling(dp)
