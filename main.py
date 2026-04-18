import os
import json
import random
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("No TOKEN provided")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

JSON_FILE = "data.json"

GIF_ROULETTE = "CgACAgQAAxkBAAFHdp1p4vZvtNFn0-k9ncI_X2ZBgAwvTAAC6wYAAjJmPFDhjlHaIPdqszsE"

START_BALANCE = 5000
BONUS_AMOUNT = 10000


# ================== DATA ==================
def load_data():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f)


def get_user(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "balance": START_BALANCE,
            "bonus": False
        }
        save_data(data)

    return data


# ================== STATES ==================
class GameState(StatesGroup):
    roulette = State()
    mines = State()
    joker = State()


# ================== KEYBOARD ==================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🎲 Рулетка")
    kb.add("💣 Мины", "🃏 Джокер")
    kb.add("🏆 Бонус", "❌ Отмена")
    return kb


# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    data = get_user(message.from_user.id)
    save_data(data)

    await message.answer(
        f"🎮 Добро пожаловать!\n💰 Баланс: {data[str(message.from_user.id)]['balance']} FRN",
        reply_markup=main_kb()
    )


# ================== BALANCE ==================
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(message: types.Message):
    data = get_user(message.from_user.id)
    bal = data[str(message.from_user.id)]["balance"]

    await message.answer(f"💰 Баланс: {bal} FRN")


# ================== ROULETTE ==================
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roulette_start(message: types.Message):
    await GameState.roulette.set()
    await message.answer("🎲 Введи: число ставка (0-36 100)")


@dp.message_handler(state=GameState.roulette)
async def roulette_play(message: types.Message, state: FSMContext):
    data = get_user(message.from_user.id)
    uid = str(message.from_user.id)

    try:
        number, bet = map(int, message.text.split())

        if not (0 <= number <= 36) or bet <= 0:
            raise ValueError

        if data[uid]["balance"] < bet:
            await message.answer("❌ Недостаточно средств")
            return

        # списание ставки
        data[uid]["balance"] -= bet
        save_data(data)

        # GIF
        await bot.send_animation(
            message.chat.id,
            GIF_ROULETTE,
            caption="🎲 Крутим рулетку..."
        )

        await asyncio.sleep(2)

        win_num = random.randint(0, 36)

        if number == win_num:
            win = bet * 35
            data[uid]["balance"] += win
            result = f"🎉 WIN +{win} FRN"
        else:
            result = f"😢 LOSS -{bet} FRN"

        save_data(data)

        await message.answer(
            f"🎲 Твоё число: {number}\n"
            f"🏁 Выпало: {win_num}\n"
            f"{result}\n"
            f"💰 Баланс: {data[uid]['balance']} FRN",
            reply_markup=main_kb()
        )

        await state.finish()

    except:
        await message.answer("❌ Формат: число ставка (пример: 17 100)")


# ================== MINES ==================
@dp.message_handler(lambda m: m.text == "💣 Мины")
async def mines_start(message: types.Message):
    await GameState.mines.set()
    await message.answer("💣 Введи ставку")


@dp.message_handler(state=GameState.mines)
async def mines_play(message: types.Message, state: FSMContext):
    data = get_user(message.from_user.id)
    uid = str(message.from_user.id)

    try:
        bet = int(message.text)

        if bet <= 0:
            raise ValueError

        if data[uid]["balance"] < bet:
            await message.answer("❌ Недостаточно средств")
            return

        mines = random.sample(range(20), 5)

        await state.update_data(
            bet=bet,
            mines=mines,
            opened=[]
        )

        data[uid]["balance"] -= bet
        save_data(data)

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(*[types.KeyboardButton(str(i)) for i in range(20)])
        kb.add("cash")

        await message.answer("💣 Выбирай клетки (0-19) или cash", reply_markup=kb)

    except:
        await message.answer("❌ Введи ставку числом")


@dp.message_handler(state=GameState.mines)
async def mines_game(message: types.Message, state: FSMContext):
    data = get_user(message.from_user.id)
    uid = str(message.from_user.id)
    st = await state.get_data()

    if message.text == "cash":
        opened = len(st.get("opened", []))
        win = int(st["bet"] * (1.3 ** opened))

        data[uid]["balance"] += win
        save_data(data)

        await message.answer(f"💰 Забрал {win} FRN", reply_markup=main_kb())
        await state.finish()
        return

    try:
        cell = int(message.text)

        if cell in st["mines"]:
            await message.answer("💥 БОМБА! Ты проиграл")
            await state.finish()
            return

        opened = st.get("opened", [])
        opened.append(cell)

        await state.update_data(opened=opened)

        await message.answer(f"✅ Safe! открыто: {len(opened)}")

    except:
        await message.answer("❌ Выбери 0-19")


# ================== BONUS ==================
@dp.message_handler(lambda m: m.text == "🏆 Бонус")
async def bonus(message: types.Message):
    data = get_user(message.from_user.id)
    uid = str(message.from_user.id)

    if not data[uid]["bonus"]:
        data[uid]["balance"] += BONUS_AMOUNT
        data[uid]["bonus"] = True
        save_data(data)
        await message.answer("🎁 +10000 FRN бонус!")
    else:
        await message.answer("❌ Уже забрал бонус")


# ================== CANCEL ==================
@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("🏠 Главное меню", reply_markup=main_kb())


# ================== RUN ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
