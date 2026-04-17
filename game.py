import os
import random
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users.json"

users = {}
bets = {}
last_numbers = []
first_bonus = set()

# ---------- SAVE / LOAD ----------

def load_users():
    global users
    try:
        with open(DATA_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)


# ---------- USER ----------

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"balance": 0}
        save_users()
    return users[uid]


# ---------- START ----------

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    u = get_user(msg.from_user.id)

    if msg.from_user.id not in first_bonus:
        u["balance"] += 5000
        first_bonus.add(msg.from_user.id)
        save_users()

    await msg.answer("🎰 Fareyn’s Casino\n💰 Баланс: {} FRN".format(u["balance"]))


# ---------- BALANCE ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "б")
async def bal(msg: types.Message):
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 {u['balance']} FRN")


# ---------- JOKER / HELL START ----------

@dp.message_handler(lambda m: m.text and (m.text.lower().startswith("джокер") or m.text.lower().startswith("хел")))
async def joker_start(msg: types.Message):
    uid = msg.from_user.id
    u = get_user(uid)

    try:
        parts = msg.text.split()
        bet = int(parts[1])

        if u["balance"] < bet:
            return await msg.answer("❌ нет денег")

        u["balance"] -= bet
        save_users()

        # создаём игру
        bets[uid] = {
            "bet": bet,
            "mult": 1.0
        }

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("❓", callback_data=f"joker|{uid}")
        )

        await msg.answer("🎲 Выбери карту:", reply_markup=keyboard)

    except:
        await msg.answer("❌ пример: джокер 100")


# ---------- JOKER CLICK ----------

@dp.callback_query_handler(lambda c: c.data.startswith("joker"))
async def joker_click(call: types.CallbackQuery):
    uid = int(call.data.split("|")[1])
    user_id = call.from_user.id

    if uid != user_id:
        return await call.answer("Это не твоя игра ❌", show_alert=True)

    if uid not in bets:
        return await call.answer("Игра не найдена")

    game = bets[uid]

    keyboard = types.InlineKeyboardMarkup()

    # шанс
    roll = random.randint(1, 100)

    if roll < 20:
        # череп
        keyboard.add(types.InlineKeyboardButton("💀", callback_data=f"lose|{uid}"))
        await call.message.edit_text("💀 ОЙ! риск карта")
    else:
        # множитель
        game["mult"] *= 1.33

        keyboard.add(
            types.InlineKeyboardButton("❓", callback_data=f"joker|{uid}")
        )
        keyboard.add(
            types.InlineKeyboardButton("💰 Забрать", callback_data=f"cash|{uid}")
        )

        await call.message.edit_text(f"✨ множитель: x{game['mult']:.2f}", reply_markup=keyboard)

    bets[uid] = game


# ---------- CASH OUT ----------

@dp.callback_query_handler(lambda c: c.data.startswith("cash"))
async def cash(call: types.CallbackQuery):
    uid = int(call.data.split("|")[1])

    if uid not in bets:
        return await call.answer()

    game = bets.pop(uid)

    u = get_user(uid)

    win = int(game["bet"] * game["mult"])
    u["balance"] += win

    save_users()

    await call.message.edit_text(f"💰 Вы забрали: +{win} FRN 🎉")


# ---------- LOSE ----------

@dp.callback_query_handler(lambda c: c.data.startswith("lose"))
async def lose(call: types.CallbackQuery):
    uid = int(call.data.split("|")[1])

    if uid in bets:
        bets.pop(uid)

    await call.message.edit_text("💀 ПРОИГРЫШ ❌")


# ---------- SIMPLE BET GAME ----------

@dp.message_handler(lambda m: m.text and m.text[0].isdigit())
async def bet(msg: types.Message):
    u = get_user(msg.from_user.id)

    try:
        amount = int(msg.text.split()[0])

        if u["balance"] < amount:
            return await msg.answer("❌ нет денег")

        u["balance"] -= amount
        save_users()

        await msg.answer(f"🎲 ставка {amount} FRN принята")

    except:
        pass


# ---------- RUN ----------

if __name__ == "__main__":
    load_users()
    executor.start_polling(dp)
