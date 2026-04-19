import asyncio
import random
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

# ================== НАСТРОЙКИ ==================
API_TOKEN = "ВАШ_ТОКЕН_ТУТ"  # Вставь сюда токен от @BotFather
ADMIN_ID = 0  # Твой ID (числами)
DB_PATH = "casino.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== РАБОТА С БАЗОЙ ==================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 5000)")
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

# ================== ЛОГИКА ИГРЫ ==================
RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
active_games = {} # Храним состояние для каждого чата

@dp.message(Command("start"))
async def cmd_start(m: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 GO"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📊 Лог")]
    ], resize_keyboard=True)
    await m.answer("🎰 Казино готово к работе!", reply_markup=kb)

@dp.message(F.text == "💰 Баланс")
async def check_bal(m: Message):
    b = await get_val(m.from_user.id)
    await m.answer(f"💰 Ваш баланс: {b:,} FRN")

@dp.message(F.text == "📊 Лог")
async def show_log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT num FROM history ORDER BY id DESC LIMIT 10") as c:
            rows = await c.fetchall()
            if not rows: return await m.answer("История пуста")
            res = "📊 Последние 10 чисел:\n"
            for r in rows:
                emoji = "🟢" if r[0] == 0 else ("🔴" if r[0] in RED else "⚫️")
                res += f"{emoji} {r[0]}\n"
            await m.answer(res)

@dp.message(F.text == "🚀 GO")
async def start_go(m: Message):
    cid = m.chat.id
    if cid in active_games and active_games[cid]['status']:
        return await m.answer("⏳ Раунд уже идет!")
    
    active_games[cid] = {'status': True, 'bets': []}
    await m.answer("🎰 СТАВКИ ОТКРЫТЫ (15 сек)\nПример: `100 к` (на красное)")
    
    await asyncio.sleep(15)
    
    game = active_games[cid]
    game['status'] = False
    if not game['bets']:
        return await m.answer("❌ Ставок нет, отмена.")

    win_num = random.randint(0, 36)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO history (num) VALUES (?)", (win_num,))
        await db.commit()

    emoji = "🟢" if win_num == 0 else ("🔴" if win_num in RED else "⚫️")
    res_msg = f"🎰 Выпало: {win_num} {emoji}\n\n"
    
    for b in game['bets']:
        mult = 0
        if b['type'] == 'к' and win_num in RED: mult = 1.95
        elif b['type'] == 'ч' and win_num not in RED and win_num != 0: mult = 1.95
        elif b['type'].isdigit() and int(b['type']) == win_num: mult = 35
        
        if mult > 0:
            win_cash = int(b['amount'] * mult)
            await update_balance(b['uid'], win_cash)
            res_msg += f"🏆 {b['name']} выиграл {win_cash:,}!\n"
    
    await m.answer(res_msg)

@dp.message()
async def take_bet(m: Message):
    cid = m.chat.id
    if cid not in active_games or not active_games[cid]['status']: return
    
    try:
        parts = m.text.lower().split()
        amount = int(parts[0])
        b_type = parts[1]
        
        bal = await get_val(m.from_user.id)
        if bal < amount: return await m.answer("❌ Нет денег!")
        
        await update_balance(m.from_user.id, -amount)
        active_games[cid]['bets'].append({
            'uid': m.from_user.id, 'name': m.from_user.first_name,
            'amount': amount, 'type': b_type
        })
        await m.answer(f"✅ Ставка принята: {amount} на {b_type}")
    except: pass

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
