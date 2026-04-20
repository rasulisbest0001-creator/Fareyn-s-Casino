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
# Берем данные из переменных окружения
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = "casino.db"

if not API_TOKEN:
    logging.error("API_TOKEN не найден в переменных окружения!")
    exit(1)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарь для хранения состояний игр в разных чатах
active_games = {}

# ================= DB FUNCTIONS =================
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
        CREATE TABLE IF NOT EXISTS wins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            bet TEXT,
            win_num INTEGER,
            time INTEGER
        )
        """)
        await db.commit()

async def ensure_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
        await db.commit()

async def get_balance(uid):
    await ensure_user(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE id=?", (uid,)) as c:
            r = await c.fetchone()
            return r[0] if r else 5000

async def change_balance(uid, amount):
    await ensure_user(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))
        await db.commit()

# ================= HANDLERS =================

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await ensure_user(m.from_user.id)
    bal = await get_balance(m.from_user.id)
    await m.answer(f"Привет! Твой баланс: {bal} 💰\nЧтобы начать игру, напиши: 🚀 GO")

@dp.message(F.text.lower() == "лог")
async def show_log(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, amount, bet, win_num, time
            FROM wins
            ORDER BY id DESC LIMIT 10
        """) as c:
            rows = await c.fetchall()

    if not rows:
        return await m.answer("История выигрышей пуста.")

    text = "📊 **Последние 10 выигрышей:**\n\n"
    for uid, amount, bet, win_num, t in rows:
        tm = time.strftime("%H:%M", time.localtime(t))
        text += f"👤 `{uid}` | 🎯 {bet} | 💰 +{amount} | 🎰 Выпало: {win_num} | ⏰ {tm}\n"
    
    await m.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🚀 GO")
async def start_game(m: Message):
    cid = m.chat.id
    
    if cid in active_games and active_games[cid]["status"]:
        return await m.answer("⏳ Игра уже идет!")

    active_games[cid] = {
        "status": True,
        "bets": {}
    }

    await m.answer("🎰 Ставки открыты! У вас 15 секунд.\nФормат: `[сумма] [число или диапазон]`\nПример: `100 5` или `50 1-12`", parse_mode="Markdown")

    await asyncio.sleep(15)

    game_data = active_games[cid]
    game_data["status"] = False
    
    win_num = random.randint(0, 36)
    
    total_bets_count = 0
    total_bet_sum = 0
    total_win_sum = 0
    winners_text = ""

    # Обработка результатов
    for uid, user_bets in game_data["bets"].items():
        for bet_val, amount in user_bets.items():
            total_bets_count += 1
            total_bet_sum += amount
            
            is_win = False
            multiplier = 0

            # Проверка диапазона (например, 1-12)
            if "-" in bet_val:
                try:
                    start, end = map(int, bet_val.split("-"))
                    if start <= win_num <= end:
                        is_win = True
                        # Коэффициент зависит от размера диапазона
                        multiplier = 36 // (end - start + 1)
                except: continue
            
            # Проверка конкретного числа
            elif bet_val.isdigit():
                if int(bet_val) == win_num:
                    is_win = True
                    multiplier = 36

            if is_win:
                prize = amount * multiplier
                total_win_sum += prize
                await change_balance(uid, prize)
                
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("""
                        INSERT INTO wins (user_id, amount, bet, win_num, time)
                        VALUES (?, ?, ?, ?, ?)
                    """, (uid, prize, bet_val, win_num, int(time.time())))
                    await db.commit()
                
                winners_text += f"👤 {uid}: +{prize} (на {bet_val})\n"

    # Итоговое сообщение
    res_text = (
        f"🎰 **ВЫПАЛО ЧИСЛО: {win_num}**\n\n"
        f"📊 **ИТОГИ РАУНДА:**\n"
        f"Всего ставок: {total_bets_count}\n"
        f"Общая сумма: {total_bet_sum}\n"
        f"Выплачено: {total_win_sum}\n\n"
        f"🏆 **ПОБЕДИТЕЛИ:**\n"
        f"{winners_text if winners_text else 'Победителей нет.'}"
    )
    
    await m.answer(res_text, parse_mode="Markdown")
    del active_games[cid]

@dp.message()
async def place_bet(m: Message):
    cid = m.chat.id
    uid = m.from_user.id

    # Проверяем, идет ли набор ставок
    if cid not in active_games or not active_games[cid]["status"]:
        return

    try:
        parts = m.text.split()
        if len(parts) < 2: return
        
        amount = int(parts[0])
        if amount <= 0: return
        
        bets_list = parts[1:]
        total_needed = amount * len(bets_list)

        balance = await get_balance(uid)
        if balance < total_needed:
            return await m.answer(f"❌ Недостаточно средств! Баланс: {balance}")

        await change_balance(uid, -total_needed)

        game = active_games[cid]
        if uid not in game["bets"]:
            game["bets"][uid] = {}

        for b in bets_list:
            game["bets"][uid][b] = game["bets"][uid].get(b, 0) + amount

        await m.answer(f"✅ Ставка {total_needed} принята!")
    except ValueError:
        pass # Игнорируем текст, который не является ставкой

# ================= MAIN =================
async def main():
    await init_db()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
