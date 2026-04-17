import os
import random
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users.json"

users = {}
bets = []
joker_games = {}
mines_games = {}
first_bonus = set()


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
        users[uid] = {
            "balance": 0,
            "best_claimed": False
        }

    return users[uid]


def name(uid):
    try:
        u = asyncio.get_event_loop().run_until_complete(bot.get_chat(uid))
        return u.username or u.first_name or str(uid)
    except:
        return str(uid)


# ================= START =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    u = get_user(msg.from_user.id)

    if msg.from_user.id not in first_bonus:
        u["balance"] += 5000
        first_bonus.add(msg.from_user.id)
        save()

    await msg.answer(f"🎰 Casino\n💰 {u['balance']} FRN")


# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "б")
async def bal(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 {u['balance']} FRN")


# ======================================================
# 🎲 ROULETTE
# ======================================================

@dp.message_handler(lambda m: m.text and m.text[0].isdigit())
async def bet(msg: types.Message):
    u = get_user(msg.from_user.id)

    parts = msg.text.split()
    amount = int(parts[0])

    if u["balance"] < amount:
        return await msg.answer("❌ нет денег")

    u["balance"] -= amount

    for b in parts[1:]:
        bets.append({
            "user": msg.from_user.id,
            "amount": amount,
            "bet": b
        })

    save()
    await msg.answer("🎲 ставка принята")


@dp.message_handler(lambda m: m.text == "го")
async def spin(msg: types.Message):
    global bets

    if not bets:
        return await msg.answer("❌ нет ставок")

    num = random.randint(0, 36)
    color = "🟢" if num == 0 else ("🔴" if num % 2 else "⚫")

    text = f"🎯 {num} {color}\n\n"

    for b in bets:
        u = get_user(b["user"])

        win = False
        coef = 0

        if str(num) == str(b["bet"]):
            win, coef = True, 35
        elif b["bet"] == "к" and color == "🔴":
            win, coef = True, 2
        elif b["bet"] == "ч" and color == "⚫":
            win, coef = True, 2

        if win:
            win_money = b["amount"] * coef
            u["balance"] += win_money
            text += f"✅ {name(b['user'])} +{win_money}\n"
        else:
            text += f"❌ {name(b['user'])}\n"

    bets = []
    save()
    await msg.answer(text)


# ======================================================
# 🃏 JOKER / HELL
# ======================================================

@dp.message_handler(lambda m: m.text and (m.text.startswith("джокер") or m.text.startswith("хел")))
async def joker(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    bet = int(msg.text.split()[1])

    if u["balance"] < bet:
        return await msg.answer("❌ нет денег")

    u["balance"] -= bet
    save()

    joker_games[uid] = {"bet": bet, "mult": 1.0}

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❓", callback_data=f"jk|{uid}"))

    await msg.answer("🃏 игра началась", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("jk"))
async def jk(call: types.CallbackQuery):
    uid = int(call.data.split("|")[1])

    game = joker_games.get(uid)
    if not game:
        return

    if random.randint(1, 100) < 25:
        joker_games.pop(uid)
        return await call.message.edit_text("💀 ЛОСЕР ❌")

    game["mult"] *= 1.33

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❓", callback_data=f"jk|{uid}"))
    kb.add(types.InlineKeyboardButton("💰 забрать", callback_data=f"cash|{uid}"))

    await call.message.edit_text(f"✨ x{game['mult']:.2f}", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("cash"))
async def cash(call: types.CallbackQuery):
    uid = int(call.data.split("|")[1])

    game = joker_games.pop(uid)
    u = get_user(uid)

    win = int(game["bet"] * game["mult"])
    u["balance"] += win
    save()

    await call.message.edit_text(f"💰 +{win} FRN")


# ======================================================
# 💣 MINES (5x4 / 7 mines)
# ======================================================

MINES_SIZE = 20
MINES_COUNT = 7


@dp.message_handler(lambda m: m.text and m.text.startswith("мины"))
async def mines_start(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    bet = int(msg.text.split()[1])

    if u["balance"] < bet:
        return await msg.answer("❌ нет денег")

    u["balance"] -= bet
    save()

    mines = set(random.sample(range(MINES_SIZE), MINES_COUNT))

    mines_games[uid] = {
        "bet": bet,
        "mines": mines,
        "opened": set(),
        "mult": 1.0
    }

    await msg.answer("💣 игра мины началась (0–19)")


@dp.message_handler(lambda m: m.text and m.text.startswith("к"))
async def mines_click(msg: types.Message):
    uid = msg.from_user.id

    game = mines_games.get(uid)
    if not game:
        return

    idx = int(msg.text.split()[1])

    if idx in game["opened"]:
        return await msg.answer("уже открыто")

    if idx in game["mines"]:
        mines_games.pop(uid)
        return await msg.answer("💥 МИНА! ЛОСЕР ❌")

    game["opened"].add(idx)
    game["mult"] *= 1.3

    await msg.answer(f"✨ x{game['mult']:.2f}\n(напиши 'забрать')")


@dp.message_handler(lambda m: m.text == "забрать")
async def mines_cash(msg: types.Message):
    uid = msg.from_user.id

    game = mines_games.pop(uid, None)
    if not game:
        return

    u = get_user(uid)

    win = int(game["bet"] * game["mult"])
    u["balance"] += win
    save()

    await msg.answer(f"💰 +{win} FRN 🎉")


# ======================================================
# 🔥 BONUS COMMANDS
# ======================================================

@dp.message_handler(lambda m: m.text and m.text.lower() == "fareyntop")
async def top(msg: types.Message):
    u = get_user(msg.from_user.id)

    u["balance"] += 1231231
    save()

    await msg.answer("🔥 +1231231 FRN")


@dp.message_handler(lambda m: m.text and m.text.lower() == "лучший бот")
async def best(msg: types.Message):
    u = get_user(msg.from_user.id)

    if u["best_claimed"]:
        return await msg.answer("❌ уже получал")

    u["balance"] += 5555
    u["best_claimed"] = True
    save()

    await msg.answer("🏆 +5555 FRN")


# ================= RUN =================

if __name__ == "__main__":
    load()
    executor.start_polling(dp)
