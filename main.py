import asyncio
import random
import sqlite3
import time

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = "ТВОЙ_ТОКЕН"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ---------- DB ----------
conn = sqlite3.connect("casino.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 5000
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number INTEGER,
    color TEXT
)
""")

conn.commit()

# ---------- GAME ----------
games = {}

def color(n):
    if n == 0:
        return "🟢"
    reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    return "🔴" if n in reds else "⚫"

# ---------- USER ----------
def get(uid):
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    r = cur.fetchone()

    if not r:
        cur.execute("INSERT INTO users (id, balance) VALUES (?, 5000)", (uid,))
        conn.commit()
        return 5000

    return r[0]

def update(uid, amt):
    bal = get(uid) + amt
    if bal < 0:
        return False

    cur.execute("UPDATE users SET balance=? WHERE id=?", (bal, uid))
    conn.commit()
    return True

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer(f"🎰 Casino Bot\n💰 {get(m.from_user.id)} FRN")

# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text and m.text.lower() == "баланс")
async def bal(m: types.Message):
    await m.answer(f"💰 {get(m.from_user.id)} FRN")

# ---------- TRANSFER ----------
@dp.message_handler(lambda m: m.text and m.text.startswith("п"))
async def transfer(m: types.Message):
    parts = m.text.split()

    try:
        if len(parts) == 2 and m.reply_to_message:
            uid_to = m.reply_to_message.from_user.id
            amt = int(parts[1])
        else:
            uid_to = int(parts[1])
            amt = int(parts[2])
    except:
        return await m.answer("❌ формат: п id сумма")

    if get(m.from_user.id) < amt:
        return await m.answer("❌ не хватает денег")

    update(m.from_user.id, -amt)
    update(uid_to, amt)

    await m.answer(f"💸 переведено {amt}")

# ---------- BET ----------
@dp.message_handler(lambda m: m.chat.type != "private")
async def bet(m: types.Message):
    if not m.text:
        return

    try:
        amount, bet = m.text.split()
        amount = int(amount)
    except:
        return

    uid = m.from_user.id
    chat = m.chat.id

    if amount < 10 or amount > 100000:
        return

    if get(uid) < amount:
        return await m.answer("❌ не хватает денег")

    update(uid, -amount)

    if chat not in games:
        games[chat] = []
        asyncio.create_task(run(chat))

    games[chat].append((uid, amount, bet.lower()))

    await m.answer(f"✅ ставка {amount} на {bet}")

# ---------- GAME ENGINE ----------
async def run(chat):
    await asyncio.sleep(15)

    if chat not in games:
        return

    roll = random.randint(0, 36)
    c = color(roll)

    winners = []

    for uid, amt, bet in games[chat]:
        win = 0

        try:
            if bet.isdigit() and int(bet) == roll:
                win = amt * 30

            elif "-" in bet:
                a, b = map(int, bet.split("-"))
                if a <= roll <= b:
                    win = amt * 2

            elif bet == "к" and c == "🔴":
                win = amt * 2

            elif bet == "ч" and c == "⚫":
                win = amt * 2
        except:
            continue

        if win:
            update(uid, win)
            winners.append(f"{uid} +{win}")

    cur.execute("INSERT INTO history (number,color) VALUES (?,?)", (roll, c))
    conn.commit()

    await bot.send_message(chat, f"🎲 {roll} {c}\n\n" + ("\n".join(winners) or "никто не выиграл"))

    del games[chat]

# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
