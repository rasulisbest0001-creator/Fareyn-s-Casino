import os
import random
import asyncio
import aiosqlite
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ================== CONFIG ==================
API_TOKEN = "PASTE_TOKEN_HERE"
ADMIN_ID = 123456789  # твой Telegram ID
DB = "casino.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== DB ==================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 5000
        )
        """)
        await db.commit()

async def get_balance(uid: int):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM users WHERE id=?", (uid,))
        row = await cur.fetchone()

        if not row:
            await db.execute("INSERT INTO users (id, balance) VALUES (?, 5000)", (uid,))
            await db.commit()
            return 5000

        return row[0]

async def add_balance(uid: int, amount: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))
        await db.commit()

async def set_balance(uid: int, amount: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance=? WHERE id=?", (amount, uid))
        await db.commit()

# ================== GAME ==================
class Game:
    def __init__(self):
        self.active = False
        self.accepting = False
        self.lock = asyncio.Lock()
        self.bets = {}

game = Game()

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

def mult(bet, num):
    if bet.isdigit():
        return 35 if int(bet) == num else 0

    if "-" in bet:
        try:
            a, b = map(int, bet.split("-"))
            return 3 if a <= num <= b else 0
        except:
            return 0

    if num == 0:
        return 0

    if bet in ["к", "красное"] and num in RED:
        return 2

    if bet in ["ч", "черное", "чёрное"] and num not in RED:
        return 2

    if bet in ["чет", "чёт"] and num % 2 == 0:
        return 2

    if bet in ["нечет", "нечёт"] and num % 2 == 1:
        return 2

    return 0

# ================== UI ==================
def kb():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🚀 GO"), KeyboardButton(text="💰 Баланс"))
    b.row(KeyboardButton(text="❌ Отмена"))
    return b.as_markup(resize_keyboard=True)

# ================== START ==================
@dp.message(Command("start"))
async def start(m: Message):
    await get_balance(m.from_user.id)
    await m.answer("🎰 CASINO PRO MAX", reply_markup=kb())

# ================== BALANCE ==================
@dp.message(F.text == "💰 Баланс")
async def balance(m: Message):
    b = await get_balance(m.from_user.id)
    await m.answer(f"💰 Баланс: {b:,} FRN")

# ================== ADMIN ==================
@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ нет доступа")

    await m.answer(
        "🛠 ADMIN PANEL\n\n"
        "/setbal id amount\n"
        "/addbal id amount\n"
        "/stats"
    )

@dp.message(Command("setbal"))
async def setbal(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    _, uid, amount = m.text.split()
    await set_balance(int(uid), int(amount))
    await m.answer("✔ set")

@dp.message(Command("addbal"))
async def addbal(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    _, uid, amount = m.text.split()
    await add_balance(int(uid), int(amount))
    await m.answer("✔ added")

@dp.message(Command("stats"))
async def stats(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    await m.answer("📊 bot works")

# ================== CANCEL ==================
@dp.message(F.text == "❌ Отмена")
async def cancel(m: Message):
    if not game.accepting:
        return await m.answer("⛔ закрыто")

    uid = m.from_user.id

    if uid not in game.bets:
        return await m.answer("нет ставок")

    refund = sum(b["amount"] for b in game.bets[uid])

    await add_balance(uid, refund)

    del game.bets[uid]

    await m.answer(f"❌ возврат {refund:,}")

# ================== GAME ==================
@dp.message(F.text == "🚀 GO")
async def go(m: Message):

    async with game.lock:

        if game.active:
            return await m.answer("⏳ идет раунд")

        game.active = True
        game.accepting = True
        game.bets = {}

        await m.answer("🎰 СТАВКИ ОТКРЫТЫ (15s)")
        await asyncio.sleep(15)

        game.accepting = False

        await m.answer("🎲 spin...")
        await asyncio.sleep(2)

        num = random.randint(0, 36)

        winners = []

        for uid, bets in game.bets.items():

            for b in bets:

                mlt = mult(b["bet"], num)

                if mlt > 0:
                    win = b["amount"] * mlt
                    await add_balance(uid, win)
                    winners.append(f"{uid} +{win}")

        game.active = False

        await m.answer(
            f"🎰 {num}\n\n"
            + ("\n".join(winners) if winners else "❌ no winners")
        )

# ================== BET ==================
@dp.message()
async def bet(m: Message):

    if not m.text or not game.accepting:
        return

    parts = m.text.split()

    if not parts[0].isdigit():
        return

    amount = int(parts[0])
    bets = parts[1:]

    if amount < 10:
        return await m.answer("min 10")

    bal = await get_balance(m.from_user.id)

    total = amount * len(bets)

    if bal < total:
        return await m.answer("no money")

    await add_balance(m.from_user.id, -total)

    if m.from_user.id not in game.bets:
        game.bets[m.from_user.id] = []

    for b in bets:
        game.bets[m.from_user.id].append({
            "amount": amount,
            "bet": b
        })

    await m.answer("✅ accepted")

# ================== RUN ==================
async def main():
    await init_db()
    print("CASINO RUNNING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
