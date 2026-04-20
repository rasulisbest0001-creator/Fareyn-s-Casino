import asyncio
import random
import logging
import time
import aiosqlite
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

DB_PATH = "casino.db"

logging.basicConfig(level=logging.INFO)

# ================= SAFETY CHECK =================
if not API_TOKEN:
    raise ValueError("❌ API_TOKEN не задан в environment (Railway/hosting)")

try:
    ADMIN_ID = int(ADMIN_ID)
except:
    ADMIN_ID = 0

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================= DATA =================
active_games = {}

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

# ================= DB =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 5000,
            last_bonus INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num INTEGER
        )
        """)
        await db.commit()

async def ensure_user(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
        await db.commit()

async def get_balance(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE id=?", (uid,)) as c:
            row = await c.fetchone()
            return row[0] if row else 5000

async def change_balance(uid: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?",
            (amount, uid)
        )
        await db.commit()

# ================= ADMIN =================
@dp.message(Command("add"))
async def add(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid, amount = map(int, m.text.split()[1:])
        await change_balance(uid, amount)
        await m.answer(f"✅ +{amount}")
    except:
        await m.answer("❌ /add id amount")

@dp.message(Command("take"))
async def take(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid, amount = map(int, m.text.split()[1:])
        await change_balance(uid, -amount)
        await m.answer(f"➖ -{amount}")
    except:
        await m.answer("❌ /take id amount")

# ================= BONUS =================
@dp.message(F.text.lower() == "бонус")
async def bonus(m: Message):
    uid = m.from_user.id
    await ensure_user(uid)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_bonus FROM users WHERE id=?",
            (uid,)
        ) as c:
            row = await c.fetchone()
            last = row[0] if row else 0

        now = int(time.time())

        if now - last < 86400:
            return await m.answer("⏳ Уже брал бонус")

        await db.execute(
            "UPDATE users SET last_bonus=?, balance=balance+2500 WHERE id=?",
            (now, uid)
        )
        await db.commit()

    await m.answer("🎁 +2500 FRN")

# ================= BALANCE =================
@dp.message(F.text.lower().in_(["б", "баланс"]))
async def bal(m: Message):
    await ensure_user(m.from_user.id)
    b = await get_balance(m.from_user.id)
    await m.answer(f"💰 Баланс: {b}")

# ================= HISTORY =================
@dp.message(F.text == "📊 Лог")
async def log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT num FROM history ORDER BY id DESC LIMIT 10"
        ) as c:
            rows = await c.fetchall()

    if not rows:
        return await m.answer("Пусто")

    await m.answer("📊 Последние:\n" + "\n".join(str(r[0]) for r in rows))

# ================= GAME =================
@dp.message(F.text == "🚀 GO")
async def game(m: Message):
    cid = m.chat.id
    active_games[cid] = {"status": True, "bets": {}}

    await m.answer("🎰 Ставки открыты (15 сек)")

    await asyncio.sleep(15)

    game = active_games[cid]
    game["status"] = False

    win = random.randint(0, 36)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO history (num) VALUES (?)", (win,))
        await db.commit()

    text = f"🎰 Выпало: {win}\n\n🏆 Результат:\n"

    for uid, bets in game["bets"].items():
        for bet, amount in bets.items():

            win_flag = False
            mult = 0

            if "-" in bet:
                a, b = map(int, bet.split("-"))
                if a <= win <= b:
                    win_flag = True
                    mult = max(2, 36 // (b - a + 1))

            elif bet.isdigit():
                if int(bet) == win:
                    win_flag = True
                    mult = 36

            if win_flag:
                prize = amount * mult
                await change_balance(uid, prize)
                text += f"{uid} +{prize}\n"

    await m.answer(text)

# ================= BET =================
@dp.message()
async def bet(m: Message):
    cid = m.chat.id
    uid = m.from_user.id

    if cid not in active_games or not active_games[cid]["status"]:
        return

    try:
        parts = m.text.split()
        amount = int(parts[0])
        bets = parts[1:]

        bal = await get_balance(uid)
        total = amount * len(bets)

        if bal < total:
            return await m.answer("❌ Нет денег")

        await change_balance(uid, -total)

        game = active_games[cid]

        if uid not in game["bets"]:
            game["bets"][uid] = {}

        for b in bets:
            game["bets"][uid][b] = game["bets"][uid].get(b, 0) + amount

        await m.answer("✅ Принято")

    except:
        pass

# ================= START =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
