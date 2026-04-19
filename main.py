import os
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

# === TOKEN (DO NOT CHANGE THIS STRUCTURE) ===
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise Exception("API_TOKEN not found in Railway Variables")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === DATABASE (temporary memory) ===
users = {}
last_results = []

# === HELPERS ===
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 1000,
            "bets": [],
            "used_codes": []
        }
    return users[user_id]

# === START ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer("🎰 Welcome to Fareyn Casino!\nType /help to see commands.")

# === HELP ===
@dp.message_handler(commands=['help'])
async def help_cmd(message: types.Message):
    await message.answer(
        "🎮 Commands:\n"
        "/balance - check balance\n"
        "/spin - roulette\n"
        "/last - last results\n"
        "/code <name> - bonus code\n\n"
        "💡 Bets: 100 red / 50 9 / 20 1-18"
    )

# === BALANCE ===
@dp.message_handler(commands=['balance'])
async def balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"💰 Balance: {user['balance']}")

# === BONUS CODES (your idea preserved) ===
@dp.message_handler(commands=['code'])
async def code(message: types.Message):
    user = get_user(message.from_user.id)
    args = message.get_args().lower()

    if args == "best":
        if "best" not in user["used_codes"]:
            user["balance"] += 5555
            user["used_codes"].append("best")
            await message.answer("🎁 +5555 added!")
        else:
            await message.answer("❌ Already used")

    elif args == "fareyn":
        user["balance"] += 999999
        await message.answer("🎁 +999999 added!")

    else:
        await message.answer("❌ Invalid code")

# === BET SYSTEM ===
@dp.message_handler()
async def bets(message: types.Message):
    user = get_user(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        return

    try:
        amount = int(parts[0])
        bets = parts[1:]

        if len(user["bets"]) + len(bets) > 100:
            await message.answer("❌ Max 100 bets per round")
            return

        total_cost = amount * len(bets)

        if user["balance"] < total_cost:
            await message.answer("❌ Not enough balance")
            return

        for b in bets:
            user["bets"].append((amount, b))
            user["balance"] -= amount
            await message.answer(f"✅ Bet {amount} on {b} accepted")

    except:
        pass

# === ROULETTE ===
@dp.message_handler(commands=['spin'])
async def spin(message: types.Message):
    number = random.randint(0, 36)
    last_results.append(number)

    if len(last_results) > 10:
        last_results.pop(0)

    await message.answer(f"🎯 Result: {number}")

# === LAST RESULTS ===
@dp.message_handler(commands=['last'])
async def last(message: types.Message):
    await message.answer(f"📊 Last: {last_results}")

# === START BOT ===
if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
