import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data.json"

# ================== DATA ==================
def load():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, "r", encoding="utf-8"))
    return {}

def save():
    json.dump(users, open(DATA_FILE, "w", encoding="utf-8"))

users = load()

def get_user(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "баланс": 5000,
            "коды": []
        }
        save()

    return users[uid]

# ================== GAME ==================
game = {
    "активна": False,
    "ставки": [],
    "лог": []
}

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    get_user(m.from_user.id)

    await m.answer(
        "🎰 FARAIN CASINO\n\n"
        "💰 б / баланс — баланс\n"
        "🚀 go — старт раунда\n"
        "❌ отмена — отменить ставки\n\n"
        "🎲 ставки:\n"
        "500 9\n"
        "500 9-20\n"
        "500 к (красное)\n"
        "500 ч (чёрное)\n"
        "500 чет / нечет\n\n"
        "💎 FARAIN — +987654\n"
        "🎁 4999 — +4999 (1 раз)"
    )

# ================== BALANCE ==================
@dp.message_handler(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def bal(m: types.Message):
    u = get_user(m.from_user.id)
    await m.answer(f"💰 Баланс: {u['баланс']} FRN")

# ================== CODES ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "4999")
async def c1(m: types.Message):
    u = get_user(m.from_user.id)

    if "4999" not in u["коды"]:
        u["баланс"] += 4999
        u["коды"].append("4999")
        save()
        await m.answer("🎁 +4999 FRN (одноразовый)")
    else:
        await m.answer("❌ уже использован")

@dp.message_handler(lambda m: m.text and m.text.lower() == "farain")
async def c2(m: types.Message):
    u = get_user(m.from_user.id)

    u["баланс"] += 987654
    save()

    await m.answer("💎 +987654 FRN (FARAIN)")

# ================== CANCEL ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "отмена")
async def cancel(m: types.Message):
    game["ставки"] = []
    await m.answer("❌ все ставки отменены")

# ================== BET SYSTEM ==================
@dp.message_handler()
async def bet(m: types.Message):
    if not game["активна"]:
        return

    u = get_user(m.from_user.id)
    text = m.text.lower().split()

    try:
        amount = int(text[0])
        bets = text[1:]

        for b in bets:

            if u["баланс"] < amount:
                await m.answer("❌ недостаточно средств")
                continue

            u["баланс"] -= amount

            game["ставки"].append({
                "user": m.from_user.id,
                "name": m.from_user.first_name,
                "amount": amount,
                "bet": b
            })

            await m.answer(f"📥 ставка {amount} на {b} принята")

        save()

    except:
        pass

# ================== GO GAME ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "go")
async def go(m: types.Message):

    if game["активна"]:
        await m.answer("⏳ раунд уже идёт")
        return

    game["активна"] = True
    game["ставки"] = []

    await m.answer("🎰 ставки открыты! 15 секунд")

    await asyncio.sleep(15)

    number = random.randint(0, 36)

    game["лог"].append(number)
    if len(game["лог"]) > 10:
        game["лог"].pop(0)

    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]

    results = []

    for s in game["ставки"]:
        win = False

        b = s["bet"]

        # number
        if b.isdigit():
            if int(b) == number:
                win = True

        # range
        elif "-" in b:
            a, c = map(int, b.split("-"))
            if a <= number <= c:
                win = True

        # red / black
        elif b in ["к", "красное"]:
            win = number in red

        elif b in ["ч", "черное", "чёрное"]:
            win = number not in red

        # even / odd
        elif b in ["чет", "чёт", "even"]:
            win = number % 2 == 0

        elif b in ["нечет", "нечёт", "odd"]:
            win = number % 2 == 1

        if win:
            reward = s["amount"] * 2
            u = get_user(s["user"])
            u["баланс"] += reward

            results.append(
                f"🏆 {s['name']} выиграл {reward} FRN на {b} (число {number})"
            )

    save()

    game["активна"] = False

    await m.answer(
        f"🎰 РЕЗУЛЬТАТ: {number}\n\n"
        + ("\n".join(results) if results else "❌ победителей нет") +
        f"\n\n📊 лог: {game['лог']}"
    )

# ================== RUN ==================
if __name__ == "__main__":
    print("🎰 FARAIN CASINO RUNNING")
    executor.start_polling(dp, skip_updates=True)
