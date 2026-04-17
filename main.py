import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users.json"

users = {}
bets = []
mines = {}
joker = {}

# ================= MENU =================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("💰 Баланс"), KeyboardButton("🎮 Игры"))
menu.add(KeyboardButton("💣 Мины"), KeyboardButton("🃏 Джокер"))
menu.add(KeyboardButton("🏆 Бонусы"))

# ================= SAVE =================

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
        users[uid] = {"balance": 0, "best": False}
    return users[uid]

# ================= START (KINO UI) =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    u = get_user(msg.from_user.id)

    if u["balance"] == 0:
        u["balance"] += 5000

    save()

    text = (
        "🎰 𝗙𝗔𝗥𝗘𝗬𝗡 𝗖𝗔𝗦𝗜𝗡𝗢 🎰\n\n"
        "💰 Баланс: {bal} FRN\n\n"
        "🎮 ИГРЫ:\n"
        "🎲 Рулетка → число + ставка → /go\n"
        "💣 Мины → /mines ставка\n"
        "🃏 Джокер → /joker ставка\n\n"
        "🏆 БОНУСЫ:\n"
        "• /fareyntop → огромный бонус\n"
        "• /bestbot → 1 раз\n\n"
        "⚠️ FRN — виртуальная валюта"
    ).format(bal=u["balance"])

    await msg.answer(text, reply_markup=menu)

# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {u['balance']} FRN")

# ================= BONUS =================

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

    u["best"] = True
    u["balance"] += 5555
    save()

    await msg.answer("🏆 +5555 FRN")

# ================= MINES =================

@dp.message_handler(commands=["mines"])
async def mines_start(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    try:
        bet = int(msg.get_args())
    except:
        return await msg.answer("❌ /mines 100")

    if u["balance"] < bet:
        return await msg.answer("❌ нет денег")

    u["balance"] -= bet

    bombs = set(random.sample(range(20), 5))

    mines[uid] = {
        "bet": bet,
        "bombs": bombs,
        "mult": 1.0
    }

    save()

    await msg.answer_animation(
        "https://media.giphy.com/media/3o7TKtnuHOHHUjR38Y/giphy.gif",
        caption="💣 Мины запущены..."
    )

    await asyncio.sleep(2)

    await msg.answer("💣 игра началась\n/pick 0-19\n/cash")

@dp.message_handler(commands=["pick"])
async def pick(msg: types.Message):
    uid = msg.from_user.id

    if uid not in mines:
        return

    game = mines[uid]

    try:
        idx = int(msg.get_args())
    except:
        return

    if idx in game["bombs"]:
        mines.pop(uid)
        return await msg.answer("💥 LOSE")

    game["mult"] *= 1.3

    await msg.answer(f"✨ x{game['mult']:.2f}")

@dp.message_handler(commands=["cash"])
async def cash(msg: types.Message):
    uid = msg.from_user.id

    if uid not in mines:
        return

    game = mines.pop(uid)
    u = get_user(uid)

    win = int(game["bet"] * game["mult"])
    u["balance"] += win

    save()
    await msg.answer(f"💰 WIN +{win}")

# ================= JOKER =================

@dp.message_handler(commands=["joker"])
async def joker_start(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    try:
        bet = int(msg.get_args())
    except:
        return await msg.answer("❌ /joker 100")

    if u["balance"] < bet:
        return await msg.answer("❌ нет денег")

    u["balance"] -= bet

    joker[uid] = {"bet": bet, "mult": 1.0}

    save()

    await msg.answer_animation(
        "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif",
        caption="🃏 Джокер играет..."
    )

    await msg.answer("🃏 /flip")

@dp.message_handler(commands=["flip"])
async def flip(msg: types.Message):
    uid = msg.from_user.id

    if uid not in joker:
        return

    game = joker[uid]

    if random.randint(1, 100) < 30:
        joker.pop(uid)
        return await msg.answer("💀 LOSE")

    game["mult"] *= 1.33

    await msg.answer(f"✨ x{game['mult']:.2f}")

@dp.message_handler(commands=["cashjoker"])
async def cashjoker(msg: types.Message):
    uid = msg.from_user.id

    if uid not in joker:
        return

    game = joker.pop(uid)
    u = get_user(uid)

    win = int(game["bet"] * game["mult"])
    u["balance"] += win

    save()
    await msg.answer(f"💰 WIN +{win}")

# ================= ROULETTE (CLEAN + NICKS + 1 MSG) =================

@dp.message_handler(lambda m: m.text and m.text.split()[0].isdigit())
async def bet(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    parts = msg.text.split()

    try:
        number = int(parts[0])
        amount = int(parts[1])
    except:
        return

    if u["balance"] < amount:
        return await msg.answer("❌ нет денег")

    u["balance"] -= amount

    bets.append((uid, amount, number))

    await msg.answer("🎲 ставка принята")

@dp.message_handler(commands=["go"])
async def go(msg: types.Message):
    global bets

    if not bets:
        return await msg.answer("❌ нет ставок")

    await msg.answer_animation(
        "https://media.giphy.com/media/3o7TKtnuHOHHUjR38Y/giphy.gif",
        caption="🎰 Крутим рулетку..."
    )

    await asyncio.sleep(2)

    win_number = random.randint(0, 36)

    text = f"🎯 ВЫПАЛО: {win_number}\n\n🏁 РЕЗУЛЬТАТЫ:\n"

    for uid, amount, bet in bets:
        u = get_user(uid)

        try:
            user = await bot.get_chat(uid)
            name = user.first_name
        except:
            name = "Игрок"

        if bet == win_number:
            win = amount * 35
            u["balance"] += win
            text += f"✅ {name} +{win}\n"
        else:
            text += f"❌ {name} -{amount}\n"

    bets = []
    save()

    await msg.answer(text)

# ================= RUN =================

if __name__ == "__main__":
    load()
    executor.start_polling(dp)
