import os
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("NO TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

FILE = "data.json"

# ---------- DATA ----------
def load():
    try:
        return json.load(open(FILE))
    except:
        return {}

def save(data):
    json.dump(data, open(FILE, "w"))

data = load()

def user(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {"balance": 5000, "bonus": False}
    return data[uid]

# ---------- STATES ----------
class Game(StatesGroup):
    roulette = State()
    mines = State()
    joker = State()

# ---------- MENU ----------
kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb.add("💰 Баланс", "🎲 Рулетка")
kb.add("💣 Мины", "🃏 Джокер")
kb.add("❌ Отмена")

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    u = user(m.from_user.id)
    save(data)
    await m.answer(f"🎰 Casino\n💰 Баланс: {u['balance']}", reply_markup=kb)

# ---------- BALANCE ----------
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def bal(m: types.Message):
    await m.answer(f"💰 {user(m.from_user.id)['balance']} FRN")

# ---------- CANCEL ----------
@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel(m: types.Message, state: FSMContext):
    await state.finish()
    await m.answer("❌ отмена", reply_markup=kb)

# ---------- ROULETTE ----------
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def r(m: types.Message):
    await Game.roulette.set()
    await m.answer("формат: число ставка (17 100)")

@dp.message_handler(state=Game.roulette)
async def r_play(m: types.Message, state: FSMContext):
    try:
        n, b = map(int, m.text.split())
        u = user(m.from_user.id)

        if u["balance"] < b:
            return await m.answer("нет денег")

        u["balance"] -= b
        win = random.randint(0, 36)

        if win == n:
            win_money = b * 35
            u["balance"] += win_money
            text = f"🎉 WIN {win_money}"
        else:
            text = f"💀 LOSE ({win})"

        save(data)
        await state.finish()
        await m.answer(text + f"\n💰 {u['balance']}")

    except:
        await m.answer("17 100")

# ---------- MINES ----------
@dp.message_handler(lambda m: m.text == "💣 Мины")
async def mines(m: types.Message):
    await Game.mines.set()
    await m.answer("ставка:")

@dp.message_handler(state=Game.mines)
async def mines_start(m: types.Message, state: FSMContext):
    try:
        bet = int(m.text)
        u = user(m.from_user.id)

        if u["balance"] < bet:
            return await m.answer("нет денег")

        mines = random.sample(range(20), 5)

        await state.update_data(
            bet=bet,
            mines=mines,
            opened=[],
            mult=1.0
        )

        kb2 = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb2.add(*[types.KeyboardButton(str(i)) for i in range(20)])
        kb2.add("cash")

        await m.answer("💣 игра началась", reply_markup=kb2)

    except:
        await m.answer("число")

@dp.message_handler(state=Game.mines)
async def mines_play(m: types.Message, state: FSMContext):
    u = user(m.from_user.id)
    d = await state.get_data()

    if m.text == "cash":
        win = int(d["bet"] * d["mult"])
        u["balance"] += win
        save(data)
        await state.finish()
        return await m.answer(f"💰 +{win}", reply_markup=kb)

    try:
        c = int(m.text)
    except:
        return await m.answer("0-19")

    if c in d["mines"]:
        u["balance"] -= d["bet"]
        save(data)
        await state.finish()
        return await m.answer("💥 LOSE", reply_markup=kb)

    d["opened"].append(c)
    d["mult"] *= 1.3
    await state.update_data(d)

    await m.answer(f"✅ x{d['mult']:.2f}")

# ---------- JOKER ----------
@dp.message_handler(lambda m: m.text == "🃏 Джокер")
async def j(m: types.Message):
    await Game.joker.set()
    await m.answer("ставка:")

@dp.message_handler(state=Game.joker)
async def joker(m: types.Message, state: FSMContext):
    u = user(m.from_user.id)

    try:
        bet = int(m.text)

        if u["balance"] < bet:
            return await m.answer("нет денег")

        if random.random() < 0.3:
            u["balance"] -= bet
            text = "💀 lose"
        else:
            win = int(bet * 1.33)
            u["balance"] += win
            text = f"🎉 win {win}"

        save(data)
        await state.finish()
        await m.answer(text, reply_markup=kb)

    except:
        await m.answer("число")

# ---------- RUN ----------
executor.start_polling(dp, skip_updates=True)
