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

# ================== LOAD ==================
def load():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, "r"))
    return {}

def save():
    json.dump(users, open(DATA_FILE, "w"))

users = load()

def get_user(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "balance": 5000,
            "used_codes": [],
            "last_bonus": 0
        }
        save()

    return users[uid]

# ================== GAME STATE ==================
game = {
    "active": False,
    "bets": [],
    "last_results": []
}

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    get_user(m.from_user.id)

    await m.answer(
        "🎰 FARAIN CASINO PRO\n\n"
        "💰 баланс / b\n"
        "🎲 ставка: 500 9 9-20\n"
        "🚀 go — старт\n"
        "🎁 4999 — разовый код\n"
        "💎 farain — бесконечный код"
    )

# ================== BALANCE ==================
@dp.message_handler(lambda m: m.text and m.text.lower() in ["b", "баланс"])
async def bal(m: types.Message):
    u = get_user(m.from_user.id)
    await m.answer(f"💰 {u['balance']} FRN")

# ================== CODES ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "4999")
async def code_4999(m: types.Message):
    u = get_user(m.from_user.id)

    if "4999" not in u["used_codes"]:
        u["balance"] += 4999
        u["used_codes"].append("4999")
        save()
        await m.answer("🎁 +4999 FRN (one-time)")
    else:
        await m.answer("❌ already used")

@dp.message_handler(lambda m: m.text and m.text.lower() == "farain")
async def code_farain(m: types.Message):
    u = get_user(m.from_user.id)

    u["balance"] += 987654
    save()

    await m.answer("💎 +987654 FRN (FARAIN CODE)")

# ================== BET SYSTEM ==================
@dp.message_handler()
async def bet(m: types.Message):
    if not game["active"]:
        return

    u = get_user(m.from_user.id)
    text = m.text.lower().split()

    try:
        amount = int(text[0])
        bets = text[1:]

        if u["balance"] < amount * len(bets):
            await m.answer("❌ not enough FRN")
            return

        for b in bets:
            u["balance"] -= amount

            game["bets"].append({
                "user": m.from_user.id,
                "name": m.from_user.first_name,
                "amount": amount,
                "bet": b
            })

            await m.answer(f"📥 ставка {amount} на {b} принята")

        save()

    except:
        pass

# ================== GAME START ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "go")
async def go(m: types.Message):

    if game["active"]:
        await m.answer("⏳ already running")
        return

    game["active"] = True
    game["bets"] = []

    await m.answer("🎰 ставки открыты 15 сек")

    await asyncio.sleep(15)

    result = random.randint(0, 36)
    game["last_results"].append(result)

    if len(game["last_results"]) > 10:
        game["last_results"].pop(0)

    winners = []

    for b in game["bets"]:
        win = False

        # NUMBER
        if b["bet"].isdigit():
            if int(b["bet"]) == result:
                win = True

        # RANGE 9-20
        elif "-" in b["bet"]:
            a, c = b["bet"].split("-")
            if int(a) <= result <= int(c):
                win = True

        # ALL OTHER (even/odd etc placeholder)
        elif b["bet"] == "even" and result % 2 == 0:
            win = True
        elif b["bet"] == "odd" and result % 2 == 1:
            win = True

        if win:
            reward = b["amount"] * 2
            u = get_user(b["user"])
            u["balance"] += reward

            winners.append(
                f"🏆 {b['name']} выиграл {reward} на {b['bet']} (число {result})"
            )

    save()

    game["active"] = False

    await m.answer(
        f"🎰 RESULT: {result}\n\n"
        + ("\n".join(winners) if winners else "❌ нет победителей") +
        f"\n\n📊 last: {game['last_results']}"
    )

# ================== RUN ==================
if __name__ == "__main__":
    print("CASINO PRO v3 RUNNING")
    executor.start_polling(dp, skip_updates=True)
  
