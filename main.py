import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise Exception("API_TOKEN not found in Railway Variables")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data.json"

# ================== LOAD / SAVE ==================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

users = load_data()

def get_user(user_id):
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "balance": 5000,
            "last_bonus": 0,
            "used_codes": []
        }
        save_data()

    return users[uid]

# ================== GAME STATE (PER CHAT) ==================
games = {}

def get_game(chat_id):
    if chat_id not in games:
        games[chat_id] = {
            "active": False,
            "bets": [],
            "last_results": []
        }
    return games[chat_id]

# ================== START ==================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    get_user(message.from_user.id)

    await message.answer(
        "🎰 FARAIN’S CASINO\n\n"
        "📌 Commands:\n"
        "b / баланс → balance\n"
        "бонус → daily bonus\n"
        "4999 → bonus code\n"
        "ставка format: 100 red / 50 7 / 200 even\n"
        "go → start round\n"
    )

# ================== BALANCE ==================
@dp.message_handler(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💰 Balance: {user['balance']} FRN")

# ================== BONUS ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "бонус")
async def bonus(message: types.Message):
    user = get_user(message.from_user.id)
    now = asyncio.get_event_loop().time()

    if now - user.get("last_bonus", 0) >= 86400:
        user["balance"] += 2500
        user["last_bonus"] = now
        save_data()
        await message.answer("🎁 +2500 FRN bonus received!")
    else:
        await message.answer("⏳ Bonus already used (24h cooldown)")

# ================== BONUS CODE ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "4999")
async def code(message: types.Message):
    user = get_user(message.from_user.id)

    if "4999" not in user["used_codes"]:
        user["balance"] += 4999
        user["used_codes"].append("4999")
        save_data()
        await message.answer("🎁 +4999 FRN activated!")
    else:
        await message.answer("❌ Already used")

# ================== BET SYSTEM ==================
@dp.message_handler()
async def bet_handler(message: types.Message):
    user = get_user(message.from_user.id)
    game = get_game(message.chat.id)

    if not game["active"]:
        return

    text = message.text.lower().split()

    if len(text) < 2:
        return

    try:
        amount = int(text[0])
        value = text[1]

        if user["balance"] < amount:
            await message.answer("❌ Not enough FRN")
            return

        user["balance"] -= amount

        game["bets"].append({
            "user_id": message.from_user.id,
            "username": message.from_user.username or "player",
            "amount": amount,
            "value": value
        })

        save_data()

        await message.answer(f"✅ Bet accepted: {amount} on {value}")

    except:
        pass

# ================== GAME ROUND ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "go")
async def start_game(message: types.Message):
    game = get_game(message.chat.id)

    if game["active"]:
        await message.answer("⏳ Game already running")
        return

    game["active"] = True
    game["bets"] = []

    await message.answer("🎰 Betting started! You have 15 seconds...")

    await asyncio.sleep(15)

    result = random.randint(0, 36)

    game["last_results"].append(result)
    if len(game["last_results"]) > 10:
        game["last_results"].pop(0)

    winners = []
    win_text = []

    for bet in game["bets"]:
        if str(bet["value"]) == str(result):
            win_amount = bet["amount"] * 2

            user = get_user(bet["user_id"])
            user["balance"] += win_amount

            winners.append(bet["username"])
            win_text.append(f"{bet['username']} +{win_amount}")

    save_data()

    game["active"] = False
    game["bets"] = []

    await message.answer(
        f"🎰 RESULT: {result}\n\n"
        f"🏆 Winners: {len(winners)}\n"
        f"{chr(10).join(win_text) if win_text else 'No winners'}\n\n"
        f"📊 Last 10: {game['last_results']}"
    )

# ================== RUN ==================
if __name__ == "__main__":
    print("🎰 FARAIN CASINO BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
