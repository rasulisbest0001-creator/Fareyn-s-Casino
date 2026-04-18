import os
import json
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found")

# ТВОЯ ГИФКА
GIF = "CgACAgQAAxkBAAFHdp1p4vZvtNFn0-k9ncI_X2ZBgAwvTAAC6wYAAjJmPFDhjlHaIPdqszsE"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ================= DATA =================
def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

def get_user(user_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"balance": 5000, "bonus": False}
        save_data(data)
    return data[str(user_id)]

def update_balance(user_id, amount):
    data = load_data()
    data[str(user_id)]["balance"] += amount
    save_data(data)

# ================= STATES =================
class Game(StatesGroup):
    roulette = State()

# ================= KEYBOARD =================
def kb():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💰 Баланс", "🎲 Рулетка")
    keyboard.add("🏆 Бонус", "❌ Отмена")
    return keyboard

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user = get_user(msg.from_user.id)
    await msg.answer(
        f"🎮 Привет, {msg.from_user.first_name}\n💰 Баланс: {user['balance']} FRN",
        reply_markup=kb()
    )

# ================= BALANCE =================
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(msg: types.Message):
    user = get_user(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {user['balance']} FRN")

# ================= BONUS =================
@dp.message_handler(lambda m: m.text == "🏆 Бонус")
async def bonus(msg: types.Message):
    data = load_data()
    user = data[str(msg.from_user.id)]

    if not user["bonus"]:
        user["balance"] += 10000
        user["bonus"] = True
        save_data(data)
        await msg.answer("🎁 +10000 FRN")
    else:
        await msg.answer("❌ Уже забрал")

# ================= CANCEL =================
@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("❌ Отменено", reply_markup=kb())

# ================= ROULETTE =================
@dp.message_handler(lambda m: m.text == "🎲 Рулетка")
async def roulette_start(msg: types.Message):
    await Game.roulette.set()
    await msg.answer("Введи: число ставка\nПример: 17 100")

@dp.message_handler(state=Game.roulette)
async def roulette(msg: types.Message, state: FSMContext):
    try:
        number, bet = map(int, msg.text.split())

        if not (0 <= number <= 36):
            return await msg.answer("Число 0-36")

        if bet <= 0:
            return await msg.answer("Ставка > 0")

        user = get_user(msg.from_user.id)

        if user["balance"] < bet:
            return await msg.answer("💸 Нет денег")

        # крутим
        win = random.randint(0, 36)

        await bot.send_animation(msg.chat.id, GIF)

        if number == win:
            win_amount = bet * 35
            update_balance(msg.from_user.id, win_amount)
            text = f"🎉 Выпало {win}\n+{win_amount} FRN"
        else:
            update_balance(msg.from_user.id, -bet)
            text = f"😢 Выпало {win}\n-{bet} FRN"

        await msg.answer(text)
        await state.finish()

    except:
        await msg.answer("Формат: 17 100")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
