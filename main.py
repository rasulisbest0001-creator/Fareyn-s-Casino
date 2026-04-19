import os
import json
import time
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
            "balance": 5000,          # 🎁 first start bonus
            "last_bonus": 0,
            "used_codes": [],
            "bets": []
        }
        save_data()

    return users[uid]

# ================== BALANCE ==================
@dp.message_handler(lambda m: m.text.lower() in ["баланс", "б"])
async def balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💰 FRN: {user['balance']}")

# ================== DAILY BONUS ==================
@dp.message_handler(lambda m: m.text.lower() == "бонус")
async def daily_bonus(message: types.Message):
    user = get_user(message.from_user.id)
    now = time.time()

    if now - user["last_bonus"] >= 86400:
        user["balance"] += 2500
        user["last_bonus"] = now
        save_data()
        await message.answer("🎁 +2500 FRN (daily bonus)")
    else:
        await message.answer("⏳ Bonus already used (wait 24h)")

# ================== BONUS CODE ==================
@dp.message_handler(lambda m: m.text.lower() == "4999")
async def code_4999(message: types.Message):
    user = get_user(message.from_user.id)

    if "4999" not in user["used_codes"]:
        user["balance"] += 4999
        user["used_codes"].append("4999")
        save_data()
        await message.answer("🎁 +4999 FRN bonus code activated!")
    else:
        await message.answer("❌ Already used")

# ================== BET SYSTEM (SIMPLE) ==================
@dp.message_handler()
async def bets(message: types.Message):
    user = get_user(message.from_user.id)
    text = message.text.lower().split()

    if len(text) < 2:
        return

    try:
        amount = int(text[0])
        bets = text[1:]

        total = amount * len(bets)

        if user["balance"] < total:
            await message.answer("❌ Not enough FRN")
            return

        user["balance"] -= total
        save_data()

        await message.answer(f"✅ Bets accepted: {amount} x {len(bets)}")

    except:
        pass

# ================== START ==================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = get_user(message.from_user.id)
    save_data()

    await message.answer(
        "🎰 Welcome to FRN Casino!\n\n"
        "Commands:\n"
        "баланс / б → check balance\n"
        "бонус → daily +2500 FRN\n"
        "4999 → bonus code\n\n"
        "🎁 You already received 5000 FRN start bonus!"
    )

# ================== RUN ==================
if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
