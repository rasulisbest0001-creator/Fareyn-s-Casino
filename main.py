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
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = "casino.db"

if not API_TOKEN:
    raise ValueError("API_TOKEN не задан")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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
        await db.execute("""
        CREATE TABLE IF NOT EXISTS wins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            bet TEXT,
            win INTEGER,
            time INTEGER
        )
        """)
        await db.commit()

# ================= USER =================
async def ensure_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
        await db.commit()

async def get_balance(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE id=?", (uid,)) as c:
            r = await c.fetchone()
            return r[0] if r else 5000

async def change_balance(uid, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))
        await db.commit()

# ================= LOG =================
@dp.message(F.text.lower() == "лог")
async def log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, amount, bet, win, time
            FROM wins
            ORDER BY id DESC
            LIMIT 10
        """) as c:
            rows = await c.fetchall()

    if not rows:
        return await m.answer("Пусто")

    text = "📊 Последние выигрыши:\n\n"

    for uid, amount, bet, win, t in rows:
        tm = time.strftime("%H:%M", time.localtime(t))
        text += (
            f"👤 {uid}\n"
            f"🎯 {bet}\n"
            f"💰 +{amount}\n"
            f"🎰 {win}\n"
            f"⏰ {tm}\n\n"
        )

    await m.answer(text)

# ================= GAME =================
@dp.message(F.text == "🚀 GO")
async def game(m: Message):
    cid = m.chat.id

    active_games[cid] = {
        "status": True,
        "bets": {}
    }

    await m.answer("🎰 Ставки открыты (15 сек)")

    await asyncio.sleep(15)

    game = active_games[cid]
    game["status"] = False

    win = random.randint(0, 36)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO history (num) VALUES (?)", (win,))
        await db.commit()

    # ================= REPORT =================
    text = "📊 ВСЕ СТАВКИ:\n\n"

    total_bets = 0
    total_money = 0

    winners_text = "\n🏆 ВЫИГРЫШИ:\n"
    total_win_money = 0

    for uid, bets in game["bets"].items():
        for bet, amount in bets.items():

            total_bets += 1
            total_money += amount

            text += f"👤 {uid} | {amount} на {bet}\n"

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
                total_win_money += prize

                await change_balance(uid, prize)

                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("""
                        INSERT INTO wins (user_id, amount, bet, win, time)
                        VALUES (?, ?, ?, ?, ?)
                    """, (uid, prize, bet, win, int(time.time())))
                    await db.commit()

                winners_text += f"👤 {uid} +{prize} ({bet})\n"

    text += f"\n🎰 ВЫПАЛО: {win}\n"
    text += winners_text

    text += "\n📊 ИТОГ:\n"
    text += f"Ставок: {total_bets}\n"
    text += f"Поставлено: {total_money}\n"
    text += f"Выиграно: {total_win_money}\n"

    await m.answer(text)

# ================= BET =================
@dp.message()
async def bet(m: Message):
    cid = m.chat.id
    uid = m.from_user.id

    if cid not in active_games or not active_games[cid]["status"]:
        return

    if not m.text:
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

        await m.answer(f"🎰 Ставка принята")

    except:
        pass

# ================= START =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
