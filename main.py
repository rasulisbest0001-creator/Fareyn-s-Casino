import asyncio
import random
import time
import re
import aiosqlite

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType

API_TOKEN = "YOUR_TOKEN"
ADMIN_IDS = {123456789}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_PATH = "casino.db"

FIRST_BET_TIME = None
ROUND_ACTIVE = False

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


# ---------------- DB INIT ----------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 1000,
            last_bonus INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bets(
            user_id INTEGER,
            bet TEXT,
            amount INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result INTEGER
        )
        """)

        await db.commit()


# ---------------- USERS ----------------
async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        user = await cur.fetchone()
        if not user:
            await db.execute("INSERT INTO users(user_id, balance, last_bonus) VALUES(?,?,?)",
                             (uid, 1000, 0))
            await db.commit()
            return (uid, 1000, 0)
        return user


async def update_balance(uid, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?",
                         (amount, uid))
        await db.commit()


# ---------------- BETS ----------------
async def add_bet(uid, bet, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO bets VALUES(?,?,?)", (uid, bet, amount))
        await db.commit()


async def get_bets():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM bets")
        return await cur.fetchall()


async def clear_bets():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bets")
        await db.commit()


# ---------------- LOGS ----------------
async def add_log(num):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO logs(result) VALUES(?)", (num,))
        await db.commit()


async def get_logs():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT result FROM logs ORDER BY id DESC LIMIT 10")
        return await cur.fetchall()


# ---------------- HELPERS ----------------
def parse_bets(text):
    parts = text.lower().split()
    if len(parts) < 2:
        return None

    try:
        amount = int(parts[0])
        bets = parts[1:]
        return amount, bets
    except:
        return None


def check_color(num):
    if num == 0:
        return "зеленое"
    return "красное" if num in RED else "черное"


# ---------------- START ----------------
@dp.message(Command("start"))
async def start(msg: types.Message):
    await get_user(msg.from_user.id)
    await msg.answer("🎰 Казино запущено")


# ---------------- BALANCE ----------------
@dp.message(lambda m: m.text and m.text.lower() in ["баланс", "б"])
async def balance(msg):
    user = await get_user(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {user[1]}")


# ---------------- LOG ----------------
@dp.message(lambda m: m.text and m.text.lower() == "лог")
async def log(msg):
    logs = await get_logs()
    text = "📜 Последние 10:\n"
    for l in logs:
        text += str(l[0]) + " "
    await msg.answer(text)


# ---------------- CANCEL ----------------
@dp.message(lambda m: m.text and m.text.lower() == "отмена")
async def cancel(msg):
    uid = msg.from_user.id
    bets = await get_bets()

    refund = 0
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM bets WHERE user_id=?", (uid,))
        rows = await cur.fetchall()

    for r in rows:
        refund += r[2]

    await update_balance(uid, refund)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bets WHERE user_id=?", (uid,))
        await db.commit()

    await msg.answer("❌ Ставки отменены + возврат денег")


# ---------------- BETS ----------------
@dp.message()
async def bet_handler(msg: types.Message):
    global FIRST_BET_TIME, ROUND_ACTIVE

    if not msg.text:
        return

    text = msg.text.lower()

    if text in ["го", "go"]:
        if not FIRST_BET_TIME:
            return

        if time.time() - FIRST_BET_TIME < 15:
            await msg.answer("⏳ Подожди 15 секунд")
            return

        num = random.randint(0, 36)
        color = check_color(num)

        bets = await get_bets()
        winners = {}

        for uid, bet, amount in bets:
            win = 0

            if bet.isdigit() and int(bet) == num:
                win = amount * 36

            elif bet in ["к", "красное"] and color == "красное":
                win = amount * 2

            elif bet in ["ч", "черное"] and color == "черное":
                win = amount * 2

            elif bet in ["чет"] and num % 2 == 0:
                win = amount * 2

            elif bet in ["нечет"] and num % 2 == 1:
                win = amount * 2

            if win:
                await update_balance(uid, win)
                winners[uid] = win

        await add_log(num)
        await clear_bets()

        FIRST_BET_TIME = None

        text = f"🎯 Выпало: {num} ({color})\n\n"
        for u, w in winners.items():
            text += f"{u} +{w}\n"

        await msg.answer(text)
        return

    parsed = parse_bets(text)
    if not parsed:
        return

    amount, bets = parsed
    uid = msg.from_user.id
    user = await get_user(uid)

    if user[1] < amount:
        await msg.answer("Не хватает баланса")
        return

    if not FIRST_BET_TIME:
        FIRST_BET_TIME = time.time()

    for b in bets:
        await add_bet(uid, b, amount)
        await update_balance(uid, -amount)
        await msg.answer(f"✅ Ставка {amount} на {b} принята")


# ---------------- ADMIN ----------------
@dp.message()
async def admin(msg: types.Message):
    uid = msg.from_user.id

    if uid not in ADMIN_IDS:
        return

    text = msg.text.lower()

    if text.startswith("+"):
        _, user_id, amount = text.split()
        await update_balance(int(user_id), int(amount))
        await msg.answer("✅ Добавлено")

    elif text.startswith("-"):
        _, user_id, amount = text.split()
        await update_balance(int(user_id), -int(amount))
        await msg.answer("✅ Убрано")


# ---------------- MAIN ----------------
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
