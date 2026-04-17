import os
import random
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users.json"

users = {}
bets = []
last_numbers = []
start_time = None
first_bonus = set()


# ---------- SAVE / LOAD ----------

def load_users():
    global users
    try:
        with open(DATA_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}


def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)


# ---------- USER ----------

def get_user(user_id):
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = {"balance": 0}
        save_users()

    return users[user_id]


# ---------- START ----------

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    u = get_user(msg.from_user.id)

    if msg.from_user.id not in first_bonus:
        u["balance"] += 5000
        first_bonus.add(msg.from_user.id)
        save_users()

    await msg.answer(f"🎰 Fareyn’s Casino\n💰 Баланс: {u['balance']} FRN")


# ---------- BALANCE ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "б")
async def balance(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {u['balance']} FRN")


# ---------- PROFILE ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "профиль")
async def profile(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"👤 ID: {msg.from_user.id}\n💰 {u['balance']} FRN")


# ---------- LOG ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "лог")
async def log(msg: types.Message):
    if not last_numbers:
        await msg.answer("📊 пусто")
        return

    await msg.answer("\n".join(last_numbers[-10:]))


# ---------- CANCEL BETS (FIXED) ----------

@dp.message_handler(lambda m: m.text and m.text.lower().strip() == "отмена")
async def cancel(msg: types.Message):
    global bets

    uid = msg.from_user.id

    before = len(bets)
    bets = [b for b in bets if str(b["user"]) != str(uid)]
    removed = before - len(bets)

    await msg.answer(f"❌ отменено ставок: {removed}")


# ---------- TRANSFER ----------

@dp.message_handler(lambda m: m.text and m.text.lower().startswith("п "))
async def pay(msg: types.Message):
    u = get_user(msg.from_user.id)

    try:
        parts = msg.text.split()

        if msg.reply_to_message:
            target = msg.reply_to_message.from_user.id
            amount = int(parts[1])
        else:
            target = int(parts[1])
            amount = int(parts[2])

        t = get_user(target)

        if u["balance"] < amount:
            return await msg.answer("❌ нет денег")

        u["balance"] -= amount
        t["balance"] += amount

        save_users()

        await msg.answer(f"💸 переведено {amount} FRN → {target}")

    except:
        await msg.answer("❌ ошибка")


# ---------- BETS ----------

@dp.message_handler(lambda m: m.text and m.text[0].isdigit())
async def bet(msg: types.Message):
    global start_time

    parts = msg.text.split()
    user = get_user(msg.from_user.id)

    try:
        amount = int(parts[0])

        if user["balance"] < amount:
            return await msg.answer("❌ нет денег")

        for b in parts[1:]:
            bets.append({
                "user": msg.from_user.id,
                "amount": amount,
                "bet": b
            })

        await msg.answer(f"🎲 ставка {amount} FRN принята")

        if start_time is None:
            start_time = asyncio.get_event_loop().time()

    except:
        pass


# ---------- GAME ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "го")
async def go(msg: types.Message):
    global bets, start_time

    if not bets:
        return await msg.answer("❌ нет ставок")

    now = asyncio.get_event_loop().time()

    if now - start_time < 15:
        return await msg.answer(f"⏳ подожди {int(15-(now-start_time))} сек")

    num = random.randint(0, 36)
    color = "🟢" if num == 0 else ("🔴" if num % 2 == 1 else "⚫")

    last_numbers.append(f"{num} {color}")

    text = f"🎯 Выпало: {num} {color}\n\n"

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
        elif "-" in b["bet"]:
            try:
                a, c = map(int, b["bet"].split("-"))
                if a <= num <= c:
                    win, coef = True, 2
            except:
                pass

        if win:
            win_money = b["amount"] * coef
            u["balance"] += win_money
            text += f"✅ {b['user']} +{win_money}\n"
        else:
            u["balance"] -= b["amount"]
            text += f"❌ {b['user']} -{b['amount']}\n"

        save_users()

    bets = []
    start_time = None

    await msg.answer(text)


# ---------- START BOT ----------

if __name__ == "__main__":
    load_users()
    executor.start_polling(dp)
