import asyncio
import random
import logging
import time
import aiosqlite
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = "casino.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
active_games = {}

# ================= DB =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 5000, last_bonus INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, num INTEGER)")
        await db.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
        await db.commit()

async def get_balance(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE id=?", (uid,)) as c:
            r = await c.fetchone()
            return r[0] if r else 5000

async def add_balance(uid, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))
        await db.commit()

# ================= ADMIN =================
@dp.message(Command("add"))
async def add_money(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid, amount = map(int, m.text.split()[1:])
        await add_balance(uid, amount)
        await m.answer(f"✅ Добавлено {amount} пользователю {uid}")
    except:
        await m.answer("Ошибка: /add user_id amount")

@dp.message(Command("take"))
async def take_money(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid, amount = map(int, m.text.split()[1:])
        await add_balance(uid, -amount)
        await m.answer(f"➖ Забрано {amount} у {uid}")
    except:
        await m.answer("Ошибка: /take user_id amount")

# ================= BONUS =================
@dp.message(F.text.lower() == "бонус")
async def bonus(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_bonus FROM users WHERE id=?", (m.from_user.id,)) as c:
            r = await c.fetchone()
            last = r[0] if r else 0

        now = int(time.time())
        if now - last < 86400:
            return await m.answer("⏳ Уже брал бонус")

        await db.execute("UPDATE users SET last_bonus=?, balance=balance+2500 WHERE id=?", (now, m.from_user.id))
        await db.commit()

    await m.answer("🎁 +2500 FRN")

# ================= BALANCE =================
@dp.message(F.text.lower().in_(["б", "баланс"]))
async def bal(m: Message):
    b = await get_balance(m.from_user.id)
    await m.answer(f"💰 {b} FRN")

# ================= LOG =================
@dp.message(F.text == "📊 Лог")
async def log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT num FROM history ORDER BY id DESC LIMIT 10") as c:
            rows = await c.fetchall()
            if not rows:
                return await m.answer("Нет данных")
            text = "📊 Последние 10:\n"
            for r in rows:
                text += f"{r[0]}\n"
            await m.answer(text)

# ================= GAME =================
@dp.message(F.text == "🚀 GO")
async def start_game(m: Message):
    cid = m.chat.id

    active_games[cid] = {"status": True, "bets": {}}

    await m.answer("🎰 Ставки открыты (15 сек)\nПример: 300 1-5 10 20-30")

    await asyncio.sleep(15)

    game = active_games[cid]
    game["status"] = False

    win = random.randint(0, 36)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO history (num) VALUES (?)", (win,))
        await db.commit()

    result_text = f"🎰 Выпало: {win}\n\n"

    # список ставок
    for user, bets in game["bets"].items():
        for bet, amount in bets.items():
            result_text += f"{user} {amount} GRAM на {bet}\n"

    result_text += "\n🏆 РЕЗУЛЬТАТЫ:\n"

    for uid, bets in game["bets"].items():
        for bet, amount in bets.items():
            win_flag = False

            if "-" in bet:
                a, b = map(int, bet.split("-"))
                if a <= win <= b:
                    win_flag = True
                    mult = (36 // (b - a + 1))
            elif bet.isdigit():
                if int(bet) == win:
                    win_flag = True
                    mult = 36
            else:
                continue

            if win_flag:
                prize = amount * mult
                await add_balance(uid, prize)
                result_text += f"{uid} выиграл {prize}\n"

    await m.answer(result_text)

# ================= BET =================
@dp.message()
async def bet(m: Message):
    cid = m.chat.id

    if cid not in active_games or not active_games[cid]["status"]:
        return

    parts = m.text.split()

    try:
        amount = int(parts[0])
        bets = parts[1:]

        bal = await get_balance(m.from_user.id)

        total = amount * len(bets)

        if bal < total:
            return await m.answer("❌ Не хватает FRN")

        await add_balance(m.from_user.id, -total)

        game = active_games[cid]

        user = m.from_user.first_name

        if user not in game["bets"]:
            game["bets"][user] = {}

        for b in bets:
            game["bets"][user][b] = game["bets"][user].get(b, 0) + amount

        await m.answer(f"✅ Ставка принята: {user} {amount} GRAM")

    except:
        pass

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
