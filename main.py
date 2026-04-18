import os
import json
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = "ТВОЙ_ТОКЕН"
ADMIN_ID = 8530450832

CHANNEL = "@yourchannel"  # канал для подписки

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data.json"

games = {}
history = []

# ---------- DATA ----------
def load():
    try:
        with open(DATA_FILE) as f:
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
        data[uid] = {"balance": 5000}
        save(data)

    return data[uid]

def update(uid, amount):
    data = load()
    uid = str(uid)

    data[uid]["balance"] += amount
    if data[uid]["balance"] < 0:
        data[uid]["balance"] = 0

    save(data)

# ---------- COLORS ----------
def get_color(num):
    if num == 0:
        return "🟢"
    reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    return "🔴" if num in reds else "⚫"

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    uid = m.from_user.id

    try:
        member = await bot.get_chat_member(CHANNEL, uid)
        if member.status == "left":
            return await m.answer(f"Подпишись: {CHANNEL}")
    except:
        pass

    user(uid)
    await m.answer("🎰 Fareyn’s Casino\nНапиши 'б' для баланса")

# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text.lower() == "б")
async def balance(m: types.Message):
    u = user(m.from_user.id)
    await m.answer(f"💰 {u['balance']} FRN")

# ---------- TRANSFER ----------
@dp.message_handler(lambda m: m.text.startswith("п"))
async def transfer(m: types.Message):
    parts = m.text.split()

    if len(parts) == 2 and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        amount = int(parts[1])
    elif len(parts) == 3:
        uid = int(parts[1])
        amount = int(parts[2])
    else:
        return

    if user(m.from_user.id)["balance"] < amount:
        return await m.answer("❌ Нет денег")

    update(m.from_user.id, -amount)
    update(uid, amount)

    await m.answer(f"💸 Переведено {amount} FRN")

# ---------- BET ----------
@dp.message_handler(lambda m: m.chat.type != "private")
async def bet(m: types.Message):
    parts = m.text.split()

    if len(parts) != 2:
        return

    try:
        amount = int(parts[0])
        bet = parts[1].lower()
    except:
        return

    uid = m.from_user.id

    if user(uid)["balance"] < amount:
        return

    if m.chat.id not in games:
        games[m.chat.id] = {"bets": [], "start": time.time()}

    games[m.chat.id]["bets"].append((uid, amount, bet))

    await m.answer(f"✅ Ставка {amount} на {bet}")

# ---------- START GAME ----------
@dp.message_handler(lambda m: m.text.lower() == "го")
async def start_game(m: types.Message):
    chat_id = m.chat.id

    if chat_id not in games or not games[chat_id]["bets"]:
        return await m.answer("❌ Нет ставок")

    t = time.time() - games[chat_id]["start"]

    if t < 15:
        return await m.answer(f"⏳ Жди {int(15 - t)} сек")

    roll = random.randint(0, 36)
    color = get_color(roll)

    text = f"🎲 {roll} {color}\n\n"

    winners = []

    for uid, amount, bet in games[chat_id]["bets"]:
        win = False

        if bet.isdigit() and int(bet) == roll:
            win = amount * 30
        elif "-" in bet:
            a, b = map(int, bet.split("-"))
            if a <= roll <= b:
                win = amount * 2
        elif bet == "к" and color == "🔴":
            win = amount * 2
        elif bet == "ч" and color == "⚫":
            win = amount * 2

        update(uid, -amount)

        if win:
            update(uid, win)
            winners.append(f"{uid} +{win}")

    history.append(f"{roll}{color}")
    if len(history) > 10:
        history.pop(0)

    text += "\n".join(winners) if winners else "Никто не выиграл"

    await m.answer(text)

    del games[chat_id]

# ---------- LOG ----------
@dp.message_handler(lambda m: m.text.lower() == "лог")
async def log(m: types.Message):
    await m.answer(" ".join(history) if history else "Нет игр")

# ---------- ADMIN ----------
@dp.message_handler(commands=["add"])
async def add(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    amount = int(m.get_args())
    update(m.from_user.id, amount)
    await m.answer(f"+{amount}")

# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp)
