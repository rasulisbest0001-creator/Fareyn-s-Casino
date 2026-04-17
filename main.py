import os
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

FILE = "data.json"
users = {}
games = {"bets": [], "mines": {}, "joker": {}}

# ================= FSM =================

class BetState(StatesGroup):
    waiting_for_bet = State()

class MinesState(StatesGroup):
    playing = State()

class JokerState(StatesGroup):
    playing = State()

# ================= UI =================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add("💰 Баланс", "🎲 Рулетка")
menu.add("💣 Мины", "🃏 Джокер")
menu.add("🏆 Бонус")

# ================= DATA =================

def load():
    global users
    try:
        users = json.load(open(FILE))
    except:
        users = {}

def save():
    json.dump(users, open(FILE, "w"), indent=2)

def u(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"balance": 0, "bonus": False}
    return users[uid]

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    user = u(m.from_user.id)

    if user["balance"] == 0:
        user["balance"] = 5000

    save()

    await m.answer(
        f"🎰 CASINO\n\n💰 {user['balance']} FRN\n\nВыбери игру 👇",
        reply_markup=menu
    )

# ================= BALANCE =================

@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(m: types.Message):
    await m.answer(f"💰 {u(m.from_user.id)['balance']} FRN")

# ================= BONUS =================

@dp.message_handler(lambda m: m.text == "🏆 Бонус")
async def bonus(m: types.Message):
    user = u(m.from_user.id)

    if user["bonus"]:
        return await m.answer("❌ уже получено")

    user["bonus"] = True
    user["balance"] += 10000
    save()

    await m.answer("🎁 +10000 FRN")

# ================= ROULETTE FSM =================

@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roulette_start(m: types.Message):
    await BetState.waiting_for_bet.set()
    await m.answer("🎲 Введи: число ставка\nпример: 17 100")

@dp.message_handler(state=BetState.waiting_for_bet)
async def process_bet(m: types.Message, state: FSMContext):
    uid = m.from_user.id
    user = u(uid)

    try:
        num, amount = map(int, m.text.split())
    except:
        return await m.answer("❌ формат: число ставка")

    if user["balance"] < amount:
        return await m.answer("❌ нет денег")

    user["balance"] -= amount
    games["bets"].append((uid, num, amount))
    save()

    await m.answer("✅ ставка принята\nнажми /go")
    await state.finish()

@dp.message_handler(commands=["go"])
async def go(m: types.Message):
    if not games["bets"]:
        return await m.answer("❌ нет ставок")

    await m.answer_animation("https://media.tenor.com/4nXK3X9x8kAAAAAC/casino-roulette.gif")

    win = random.randint(0, 36)
    text = f"🎯 ВЫПАЛО: {win}\n\n"

    for uid, num, amount in games["bets"]:
        user = u(uid)

        try:
            name = (await bot.get_chat(uid)).first_name
        except:
            name = "Игрок"

        if num == win:
            prize = amount * 35
            user["balance"] += prize
            text += f"✅ {name} +{prize}\n"
        else:
            text += f"❌ {name} -{amount}\n"

    games["bets"] = []
    save()

    await m.answer(text)

# ================= MINES FSM =================

@dp.message_handler(lambda m: m.text == "💣 Мины")
async def mines_start(m: types.Message):
    await m.answer("💣 Введи ставку (пример: 100)")
    await MinesState.playing.set()

@dp.message_handler(state=MinesState.playing)
async def mines_game(m: types.Message, state: FSMContext):
    uid = m.from_user.id
    user = u(uid)

    if uid not in games["mines"]:
        try:
            bet = int(m.text)
        except:
            return await m.answer("❌ введи число")

        if user["balance"] < bet:
            return await m.answer("❌ нет денег")

        user["balance"] -= bet

        games["mines"][uid] = {
            "bet": bet,
            "mult": 1.0,
            "bombs": set(random.sample(range(20), 5))
        }

        save()
        return await m.answer("💣 игра началась\nнапиши число 0-19 или cash")

    game = games["mines"][uid]

    if m.text == "cash":
        win = int(game["bet"] * game["mult"])
        user["balance"] += win
        games["mines"].pop(uid)
        save()
        await state.finish()
        return await m.answer(f"💰 +{win}")

    try:
        x = int(m.text)
    except:
        return

    if x in game["bombs"]:
        games["mines"].pop(uid)
        await state.finish()
        return await m.answer("💥 проигрыш")

    game["mult"] *= 1.3
    await m.answer(f"✨ x{game['mult']:.2f}")

# ================= JOKER FSM =================

@dp.message_handler(lambda m: m.text == "🃏 Джокер")
async def joker_start(m: types.Message):
    await m.answer("🃏 Введи ставку")
    await JokerState.playing.set()

@dp.message_handler(state=JokerState.playing)
async def joker_game(m: types.Message, state: FSMContext):
    uid = m.from_user.id
    user = u(uid)

    if uid not in games["joker"]:
        try:
            bet = int(m.text)
        except:
            return await m.answer("❌ введи число")

        if user["balance"] < bet:
            return await m.answer("❌ нет денег")

        user["balance"] -= bet
        games["joker"][uid] = {"bet": bet, "mult": 1.0}
        save()

        return await m.answer("🃏 напиши: play или cash")

    game = games["joker"][uid]

    if m.text == "cash":
        win = int(game["bet"] * game["mult"])
        user["balance"] += win
        games["joker"].pop(uid)
        save()
        await state.finish()
        return await m.answer(f"💰 +{win}")

    if random.randint(1, 100) < 30:
        games["joker"].pop(uid)
        await state.finish()
        return await m.answer("💀 проигрыш")

    game["mult"] *= 1.33
    await m.answer(f"✨ x{game['mult']:.2f}")

# ================= RUN =================

if __name__ == "__main__":
    load()
    executor.start_polling(dp)
