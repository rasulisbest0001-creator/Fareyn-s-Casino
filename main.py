import asyncio
import random
import sqlite3
import time

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import Message

API_TOKEN = "ТВОЙ_ТОКЕН_СЮДА"
ADMIN_ID = 123456789  # замени на свой ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("casino.db")
cursor = db.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER,
    last_bonus INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS bets(
    user_id INTEGER,
    bet TEXT,
    amount INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result INTEGER
)""")

db.commit()

FIRST_BET_TIME = None

RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users VALUES(?,?,?)", (user_id, 1000, 0))
        db.commit()
        return (user_id, 1000, 0)
    return user

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    db.commit()

def add_bet(user_id, bet, amount):
    cursor.execute("INSERT INTO bets VALUES(?,?,?)", (user_id, bet, amount))
    db.commit()

def clear_bets():
    cursor.execute("DELETE FROM bets")
    db.commit()

def get_bets():
    cursor.execute("SELECT * FROM bets")
    return cursor.fetchall()

def add_log(num):
    cursor.execute("INSERT INTO logs(result) VALUES(?)", (num,))
    db.commit()

def get_logs():
    cursor.execute("SELECT result FROM logs ORDER BY id DESC LIMIT 10")
    return cursor.fetchall()

@dp.message(Command("start"))
async def start(msg: Message):
    get_user(msg.from_user.id)
    await msg.answer("🎰 Добро пожаловать в казино")

@dp.message()
async def handle(msg: Message):
    global FIRST_BET_TIME

    if msg.chat.type == ChatType.PRIVATE:
        if msg.text.lower() in ["баланс", "б"]:
            user = get_user(msg.from_user.id)
            await msg.answer(f"💰 Баланс: {user[1]} FRN")
        return

    text = msg.text.lower()
    user_id = msg.from_user.id
    user = get_user(user_id)

    if text in ["баланс", "б"]:
        await msg.answer(f"💰 Баланс: {user[1]} FRN")
        return

    if text == "лог":
        logs = get_logs()
        res = "📜 Последние 10:\n"
        for l in logs:
            res += str(l[0]) + " "
        await msg.answer(res)
        return

    if text == "отмена":
        cursor.execute("SELECT amount FROM bets WHERE user_id=?", (user_id,))
        bets = cursor.fetchall()
        refund = sum([b[0] for b in bets])
        update_balance(user_id, refund)
        cursor.execute("DELETE FROM bets WHERE user_id=?", (user_id,))
        db.commit()
        await msg.answer("❌ Ставки отменены, деньги возвращены")
        return

    if text.startswith("p "):
        try:
            _, uid, amount = text.split()
            uid = int(uid)
            amount = int(amount)
            if user[1] < amount:
                await msg.answer("Не хватает баланса")
                return
            update_balance(user_id, -amount)
            update_balance(uid, amount)
            await msg.answer("✅ Перевод выполнен")
        except:
            pass
        return

    if text.startswith("+") and user_id == ADMIN_ID:
        _, uid, amount = text.split()
        update_balance(int(uid), int(amount))
        await msg.answer("✅ Выдано")
        return

    if text.startswith("-") and user_id == ADMIN_ID:
        _, uid, amount = text.split()
        update_balance(int(uid), -int(amount))
        await msg.answer("✅ Списано")
        return

    if text in ["го", "go"]:
        if not FIRST_BET_TIME:
            return
        if time.time() - FIRST_BET_TIME < 15:
            await msg.answer("⏳ Подожди 15 секунд")
            return

        num = random.randint(0, 36)
        color = "зеленое" if num == 0 else ("красное" if num in RED else "черное")

        bets = get_bets()
        winners = {}

        for uid, bet, amount in bets:
            win = 0

            if bet.isdigit() and int(bet) == num:
                win = amount * 36
            elif bet in ["к", "красное"] and num in RED:
                win = amount * 2
            elif bet in ["ч", "черное"] and num not in RED and num != 0:
                win = amount * 2
            elif bet in ["чет"] and num % 2 == 0:
                win = amount * 2
            elif bet in ["нечет"] and num % 2 == 1:
                win = amount * 2

            if win > 0:
                update_balance(uid, win)
                winners[uid] = winners.get(uid, 0) + win

        add_log(num)
        clear_bets()
        FIRST_BET_TIME = None

        text = f"🎯 Выпало: {num} ({color})\n\n"
        for uid, win in winners.items():
            text += f"{uid} +{win}\n"

        await msg.answer(text)
        return

    parts = text.split()
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
            if user[1] < amount:
                await msg.answer("Не хватает баланса")
                return

            for bet in parts[1:]:
                add_bet(user_id, bet, amount)
                update_balance(user_id, -amount)
                await msg.answer(f"✅ Ставка {amount} на {bet}")

            if not FIRST_BET_TIME:
                FIRST_BET_TIME = time.time()

        except:
            pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
