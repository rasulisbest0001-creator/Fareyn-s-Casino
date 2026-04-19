import os
import random
import asyncio
import aiosqlite
import logging
from typing import Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ================== CONFIG ==================
API_TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"
ADMIN_ID = 123456789  # Твой ID
DB_PATH = "casino_ultimate.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== DATABASE SYSTEM ==================
class Database:
    def __init__(self, path):
        self.path = path

    async def execute(self, sql, params=()):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(sql, params)
            await db.commit()
            return cur

    async def fetch_one(self, sql, params=()):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(sql, params) as cur:
                return await cur.fetchone()

db = Database(DB_PATH)

async def init_db():
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 5000
        )
    """)

async def get_balance(uid: int):
    row = await db.fetch_one("SELECT balance FROM users WHERE id=?", (uid,))
    if not row:
        await db.execute("INSERT INTO users (id, balance) VALUES (?, 5000)", (uid,))
        return 5000
    return row[0]

# ================== GAME LOGIC ==================
class GameInstance:
    def __init__(self):
        self.active = False
        self.accepting = False
        self.lock = asyncio.Lock()
        self.bets: Dict[int, List[dict]] = {}
        self.history: List[int] = []

games: Dict[int, GameInstance] = {}

def get_game(chat_id: int) -> GameInstance:
    if chat_id not in games:
        games[chat_id] = GameInstance()
    return games[chat_id]

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

def get_multiplier(bet_type: str, number: int) -> float:
    if bet_type.isdigit():
        return 35.0 if int(bet_type) == number else 0.0
    if "-" in bet_type:
        try:
            a, b = map(int, bet_type.split("-"))
            return 2.8 if a <= number <= b else 0.0
        except: return 0.0
    if number == 0: return 0.0
    # Математическое преимущество казино (1.95)
    if bet_type in ["к", "красное"] and number in RED: return 1.95
    if bet_type in ["ч", "черное", "чёрное"] and number not in RED: return 1.95
    if bet_type in ["чет", "чёт"] and number % 2 == 0: return 1.95
    if bet_type in ["нечет", "нечёт"] and number % 2 == 1: return 1.95
    return 0.0

# ================== UI & KEYBOARDS ==================
def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🚀 GO"), KeyboardButton(text="💰 Баланс"))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)

# ================== HANDLERS ==================

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await get_balance(m.from_user.id)
    await m.answer(
        "🎰 <b>CASINO ULTIMATE</b>\n\n"
        "🎲 Ставка: <code>100 к</code> или <code>500 17</code>\n"
        "🚀 <b>GO</b> — запуск игры\n"
        "❌ <b>Отмена</b> — вернуть ставки",
        parse_mode="HTML", reply_markup=main_kb()
    )

@dp.message(F.text == "💰 Баланс")
async def view_balance(m: Message):
    bal = await get_balance(m.from_user.id)
    await m.answer(f"💰 Ваш баланс: <b>{bal:,} FRN</b>\n🆔 ID: <code>{m.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("admin"))
async def admin_panel(m: Message):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("🛠 <b>Admin:</b>\n\n<code>/setbal ID SUM</code>\n<code>/stats</code>", parse_mode="HTML")

@dp.message(Command("setbal"))
async def admin_setbal(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, uid, amount = m.text.split()
        await db.execute("UPDATE users SET balance=? WHERE id=?", (int(amount), int(uid)))
        await m.answer(f"✅ Баланс {uid} изменен на {amount}")
    except:
        await m.answer("Ошибка! Формат: /setbal [ID] [СУММА]")

@dp.message(F.text == "❌ Отмена")
async def cancel_bets(m: Message):
    g = get_game(m.chat.id)
    if not g.accepting: return await m.answer("⏳ Ставки уже не принимаются!")
    
    uid = m.from_user.id
    if uid not in g.bets: return await m.answer("У вас нет активных ставок.")
    
    refund = sum(b["amount"] for b in g.bets[uid])
    await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (refund, uid))
    del g.bets[uid]
    await m.answer(f"❌ Ставки возвращены: <b>{refund:,} FRN</b>", parse_mode="HTML")

@dp.message(F.text == "🚀 GO")
async def start_game(m: Message):
    g = get_game(m.chat.id)
    async with g.lock:
        if g.active: return await m.answer("⏳ Раунд уже идет!")
        
        g.active, g.accepting = True, True
        g.bets.clear()
        
        await m.answer("🎰 <b>СТАВКИ ОТКРЫТЫ! (15 секунд)</b>", parse_mode="HTML")
        await asyncio.sleep(15)
        
        g.accepting = False
        if not g.bets:
            g.active = False
            return await m.answer("❌ Ставок нет, раунд отменен.")
            
        await m.answer("🎲 Вращение колеса...")
        await asyncio.sleep(2)
        
        res = random.randint(0, 36)
        color = "🔴" if res in RED else "⚫️" if res != 0 else "🟢"
        
        winners = []
        for uid, user_bets in g.bets.items():
            for b in user_bets:
                mult = get_multiplier(b["bet"], res)
                if mult > 0:
                    win_sum = int(b["amount"] * mult)
                    await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (win_sum, uid))
                    winners.append(f"🏆 {b['name']} +{win_sum:,}")

        g.history.append(res)
        if len(g.history) > 10: g.history.pop(0)
        
        msg = f"🎰 Выпало: <b>{res} {color}</b>\n\n"
        msg += "\n".join(winners) if winners else "Никто не выиграл."
        msg += f"\n\n📊 История: <code>{g.history}</code>"
        
        g.active = False
        await m.answer(msg, parse_mode="HTML")

@dp.message()
async def process_bet(m: Message):
    g = get_game(m.chat.id)
    if not g.accepting or not m.text: return
    
    parts = m.text.lower().split()
    if not parts[0].isdigit(): return
    
    try:
        amount = int(parts[0])
        choices = parts[1:]
        if amount < 10 or not choices: return
        
        bal = await get_balance(m.from_user.id)
        total = amount * len(choices)
        
        if bal < total: return await m.answer("❌ Недостаточно средств!")
        
        await db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (total, m.from_user.id))
        
        if m.from_user.id not in g.bets: g.bets[m.from_user.id] = []
        for c in choices:
            g.bets[m.from_user.id].append({
                "name": m.from_user.first_name,
                "amount": amount,
                "bet": c
            })
        await m.answer(f"✅ Ставка принята: {total:,} FRN")
    except: pass

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
