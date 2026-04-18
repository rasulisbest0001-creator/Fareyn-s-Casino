import asyncio
import random
import sqlite3
import time

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = "ТВОЙ_ТОКЕН"
ADMIN_ID = 8530450832

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

# ---------- GAME STATE ----------
games = {}
lock_games = set()
cooldowns = {}

# ---------- COLORS ----------
def get_color(n):
    if n == 0:
        return "🟢"
    reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    return "🔴" if n in reds else "⚫"

# ---------- USERS ----------
def get_user(uid):
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    row = cur.fetchone()

    if not row:
        cur.execute("INSERT INTO users (id, balance) VALUES (?, 5000)", (uid,))
        conn.commit()
        return 5000

    return row[0]

def update(uid, amount):
    bal = get_user(uid) + amount
    if bal < 0:
        return False

    cur.execute("UPDATE users SET balance=? WHERE id=?", (bal, uid))
    conn.commit()
    return True

# ---------- ANTI SPAM ----------
def cd(uid, sec=1):
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < sec:
        return False
    cooldowns[uid] = now
    return True

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    if not cd(m.from_user.id): return
    bal = get_user(m.from_user.id)
    await m.answer(f"🎰 Casino Bot\n💰 {bal} FRN")

# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text and m.text.lower() == "баланс")
async def balance(m: types.Message):
    if not cd(m.from_user.id): return
    bal = get_user(m.from_user.id)
    await m.answer(f"💰 {bal} FRN")

# ---------- LOG ----------
@dp.message_handler(lambda m: m.text and m.text.lower() == "лог")
async def log(m: types.Message):
    cur.execute("SELECT number,color FROM history ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()

    if not rows:
        return await m.answer("Нет игр")

    await m.answer("📊 Последние 10 игр:\n" +
                   "\n".join([f"{n} {c}" for n, c in rows]))

# ---------- TRANSFER ----------
@dp.message_handler(lambda m: m.text and m.text.startswith("п"))
async def transfer(m: types.Message):
    if not cd(m.from_user.id): return

    parts = m.text.split()

    try:
        if len(parts) == 2 and m.reply_to_message:
            uid_to = m.reply_to_message.from_user.id
            amount = int(parts[1])
        else:
            uid_to = int(parts[1])
            amount = int(parts[2])
    except:
        return await m.answer("❌ формат: п id сумма")

    if amount <= 0:
        return await m.answer("❌ неверная сумма")

    if get_user(m.from_user.id) < amount:
        return await m.answer("❌ не хватает денег")

    update(m.from_user.id, -amount)
    update(uid_to, amount)

    await m.answer(f"💸 переведено {amount} FRN")

# ---------- BET ----------
@dp.message_handler(lambda m: m.chat.type != "private")
async def bet(m: types.Message):
    if not m.text:
        return

    parts = m.text.split()
    if len(parts) != 2:
        return

    try:
        amount = int(parts[0])
        bet = parts[1].lower()
    except:
        return

    if amount < 10 or amount > 100000:
        return await m.answer("❌ ставка 10–100000")

    uid = m.from_user.id
    chat = m.chat.id

    if get_user(uid) < amount:
        return await m.answer("❌ не хватает денег")

    if chat not in games:
        if chat in lock_games:
            return
        lock_games.add(chat)

        games[chat] = {
            "bets": [],
            "start": time.time()
        }

        asyncio.create_task(run_game(chat))

    update(uid, -amount)
    games[chat]["bets"].append((uid, amount, bet))

    await m.answer(f"✅ ставка {amount} на {bet}")

# ---------- GAME ENGINE ----------
async def run_game(chat):
    await asyncio.sleep(15)

    if chat not in games:
        lock_games.discard(chat)
        return

    roll = random.randint(0, 36)
    color = get_color(roll)

    winners = []

    for uid, amount, bet in games[chat]["bets"]:
        win = 0

        try:
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

        except:
            continue

        if win > 0:
            update(uid, win)
            winners.append(f"{uid} +{win}")

    cur.execute("INSERT INTO history (number,color) VALUES (?,?)", (roll, color))
    conn.commit()

    text = f"🎲 {roll} {color}\n\n"
    text += "\n".join(winners) if winners else "❌ никто не выиграл"

    await bot.send_message(chat, text)

    del games[chat]
    lock_games.discard(chat)

# ---------- RUN ----------
if __name__ == "__main__":
    executor.start_polling(dp)
