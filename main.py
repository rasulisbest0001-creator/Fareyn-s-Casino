import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("8746857507:AAHYIRxMEYJt1trNKUtzpfaFWoQBpXAhDp0")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

users = {}
bets = []
last_numbers = []
start_time = None
first_bonus = set()

# ---------------- USERS ----------------

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "joined": True
        }
    return users[user_id]


# ---------------- COLORS ----------------

def get_color(num):
    if num == 0:
        return "🟢"
    return "⚫" if num % 2 == 0 else "🔴"


# ---------------- BONUS ----------------

def give_bonus(user_id):
    if user_id not in first_bonus:
        user = get_user(user_id)
        user["balance"] += 5000
        first_bonus.add(user_id)


# ---------------- GROUP CHECK ----------------

def is_group(msg):
    return msg.chat.type in ["group", "supergroup"]


# ---------------- START ----------------

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    give_bonus(msg.from_user.id)
    u = get_user(msg.from_user.id)
    await msg.answer(f"🎰 Fareyn’s Casino\n💰 Баланс: {u['balance']} FRN")


# ---------------- BALANCE ----------------

@dp.message_handler(lambda m: m.text.lower() == "б")
async def balance(msg: types.Message):
    if not is_group(msg):
        return
    u = get_user(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {u['balance']} FRN")


# ---------------- PROFILE ----------------

@dp.message_handler(lambda m: m.text.lower() == "профиль")
async def profile(msg: types.Message):
    if not is_group(msg):
        return
    u = get_user(msg.from_user.id)
    await msg.answer(
        f"👤 ID: {msg.from_user.id}\n💰 Баланс: {u['balance']} FRN"
    )


# ---------------- LOG ----------------

@dp.message_handler(lambda m: m.text.lower() == "лог")
async def log(msg: types.Message):
    if not is_group(msg):
        return
    await msg.answer("📊 Последние числа:\n" + "\n".join(last_numbers[-10:]))


# ---------------- TRANSFER ----------------

@dp.message_handler(lambda m: m.text.startswith("п"))
async def transfer(msg: types.Message):
    if not is_group(msg):
        return

    user = get_user(msg.from_user.id)

    try:
        parts = msg.text.split()

        # reply mode
        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            amount = int(parts[1])
        else:
            target_id = int(parts[1])
            amount = int(parts[2])

        if user["balance"] < amount:
            await msg.answer("❌ Недостаточно FRN")
            return

        target = get_user(target_id)

        user["balance"] -= amount
        target["balance"] += amount

        await msg.answer(f"💸 Переведено {amount} FRN пользователю {target_id}")

    except:
        await msg.answer("❌ Ошибка перевода")


# ---------------- BET SYSTEM ----------------

@dp.message_handler(lambda m: True)
async def bet(msg: types.Message):
    global start_time

    if not is_group(msg):
        return

    parts = msg.text.lower().split()
    if len(parts) < 2:
        return

    try:
        amount = int(parts[0])
        user = get_user(msg.from_user.id)

        if user["balance"] < amount:
            await msg.answer("❌ Нет денег")
            return

        for b in parts[1:]:
            bets.append({
                "user": msg.from_user.id,
                "amount": amount,
                "bet": b
            })
            await msg.answer(f"🎲 Принята ставка {amount} FRN на {b}")

        if start_time is None:
            start_time = asyncio.get_event_loop().time()

    except:
        pass


# ---------------- GAME START ----------------

@dp.message_handler(lambda m: m.text.lower() == "го")
async def go(msg: types.Message):
    global bets, start_time

    if not is_group(msg):
        return

    if not bets:
        await msg.answer("❌ Ставки не поставлены")
        return

    now = asyncio.get_event_loop().time()

    if now - start_time < 15:
        await msg.answer(f"⏳ Подожди {int(15-(now-start_time))} сек")
        return

    num = random.randint(0, 36)
    color = get_color(num)

    last_numbers.append(f"{num} {color}")

    text = f"🎯 Выпало: {num} {color}\n\n"

    for b in bets:
        user = get_user(b["user"])
        win = False
        coef = 0

        bet = str(b["bet"])

        if bet == str(num):
            win, coef = True, 35
        elif bet == "к" and color == "🔴":
            win, coef = True, 2
        elif bet == "ч" and color == "⚫":
            win, coef = True, 2
        elif bet == "н" and num % 2 == 1:
            win, coef = True, 2
        elif bet == "ч" and num % 2 == 0:
            win, coef = True, 2
        elif "-" in bet:
            try:
                a, c = map(int, bet.split("-"))
                if a <= num <= c:
                    win, coef = True, 2
            except:
                pass

        if win:
            win_money = b["amount"] * coef
            user["balance"] += win_money
            text += f"✅ {b['user']} +{win_money} FRN\n"
        else:
            user["balance"] -= b["amount"]
            text += f"❌ {b['user']} -{b['amount']} FRN\n"

    await msg.answer(text)

    bets = []
    start_time = None


# ---------------- RUN ----------------

if __name__ == "__main__":
    executor.start_polling(dp)
