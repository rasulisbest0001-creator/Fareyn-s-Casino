import asyncio
import random
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

# ================== CONFIG ==================
API_TOKEN = "ВАШ_ТОКЕН_ТУТ" # Вставь токен от @BotFather
DB_PATH = "casino.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== DATABASE ==================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица юзеров
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 5000)")
        # Таблица истории выигрышей
        await db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, num INTEGER)")
        await db.commit()

async def update_balance(uid, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, uid))
        await db.commit()

async def get_val(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE id = ?", (uid,)) as c:
            r = await c.fetchone()
            return r[0] if r else 5000

# ================== LOGIC ==================
RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
games = {} # Состояние игры для чатов

@dp.message(Command("start"))
async def cmd_start(m: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 GO"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📊 Лог")]
    ], resize_keyboard=True)
    await m.answer("🎰 Казино запущено!\nИспользуй кнопки ниже.", reply_markup=kb)

@dp.message(F.text == "💰 Баланс")
async def check_bal(m: Message):
    b = await get_val(m.from_user.id)
    await m.answer(f"💰 Ваш баланс: {b:,} FRN")

@dp.message(F.text == "📊 Лог")
async def show_log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT num FROM history ORDER BY id DESC LIMIT 10") as c:
            rows = await c.fetchall()
            if not rows: 
                return await m.answer("История пуста. Сыграйте первый раунд!")
            
            res = "📊 <b>Последние 10 выигрышных чисел:</b>\n\n"
            for i, r in enumerate(rows, 1):
                num = r[0]
                emoji = "🟢" if num == 0 else ("🔴" if num in RED else "⚫️")
                res += f"{i}. {emoji} {num}\n"
            await m.answer(res, parse_mode="HTML")

@dp.message(F.text == "🚀 GO")
async def start_go(m: Message):
    cid = m.chat.id
    if cid in games and games[cid]['status']:
        return await m.answer("⏳ Раунд уже идет!")
    
    games[cid] = {'status': True, 'bets': []}
    await m.answer("🎰 <b>СТАВКИ ОТКРЫТЫ (15 сек)</b>\nПример: <code>100 к</code>", parse_mode="HTML")
    
    await asyncio.sleep(15)
    
    g = games[cid]
    g['status'] = False
    if not g['bets']:
        return await m.answer("❌ Ставок нет, раунд отменен.")

    win_num = random.randint(0, 36)
    
    # Сохраняем в лог (БД)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO history (num) VALUES (?)", (win_num,))
        await db.commit()

    emoji = "🟢" if win_num == 0 else ("🔴" if win_num in RED else "⚫️")
    res_msg = f"🎰 Выпало: <b>{win_num} {emoji}</b>\n\n"
    
    winners_found = False
    for b in g['bets']:
        mult = 0
        if b['type'] == 'к' and win_num in RED: mult = 1.95
        elif b['type'] == 'ч' and win_num not in RED and win_num != 0: mult = 1.95
        elif b['type'].isdigit() and int(b['type']) == win_num: mult = 35
        
        if mult > 0:
            win_cash = int(b['amount'] * mult)
            await update_balance(b['uid'], win_cash)
            res_msg += f"🏆 {b['name']} выиграл {win_cash:,} FRN!\n"
            winners_found = True
    
    if not winners_found:
        res_msg += "❌ Никто не угадал."
    
    await m.answer(res_msg, parse_mode="HTML")

@dp.message()
async def take_bet(m: Message):
    cid = m.chat.id
    if cid not in games or not games[cid]['status']: return
    
    try:
        parts = m.text.lower().split()
        amount = int(parts[0])
        b_type = parts[1]
        
        bal = await get_val(m.from_user.id)
        if bal < amount: return await m.answer("❌ Недостаточно средств!")
        
        await update_balance(m.from_user.id, -amount)
        games[cid]['bets'].append({
            'uid': m.from_user.id, 'name': m.from_user.first_name,
            'amount': amount, 'type': b_type
        })
        await m.answer(f"✅ Принято: {amount} на {b_type}")
    except: pass

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
