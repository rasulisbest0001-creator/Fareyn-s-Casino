import asyncio
import random
import re
import time
import logging
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageToDeleteNotFound

# --- КОНФИГ ---
API_TOKEN = os.getenv("BOT_TOKEN")  # через GitHub / Render / Railway
ROUND_COOLDOWN = 15
RESULT_PAUSE = 2
MAX_BETS_PER_USER = 100
DAILY_BONUS_AMOUNT = 2500

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

users = {}
active_rounds = {}

RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

# --- USER ---
def get_user(user_id, name):
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "name": name,
            "used_best": False,
            "last_bonus": 0
        }
    return users[user_id]

def get_num_data(n):
    if n == 0:
        return "🟢 0", "зеро"
    if n in RED_NUMBERS:
        return f"🔴 {n}", "к"
    return f"⚫ {n}", "ч"

# --- БОНУС ---
@dp.message_handler(lambda m: m.text.lower() == "бонус")
async def bonus(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    now = time.time()

    if now - u["last_bonus"] >= 86400:
        u["balance"] += DAILY_BONUS_AMOUNT
        u["last_bonus"] = now
        await message.answer(f"+{DAILY_BONUS_AMOUNT} FRN")
    else:
        rem = int(86400 - (now - u["last_bonus"]))
        await message.answer(f"жди {rem//3600}ч {rem%3600//60}м")

# --- ПРОМО ---
@dp.message_handler(lambda m: m.text == "Лучший")
async def best(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    if u["used_best"]:
        await message.answer("уже использовал")
    else:
        u["balance"] += 5555
        u["used_best"] = True
        await message.answer("+5555 FRN")

@dp.message_handler(lambda m: m.text == "Фарейн")
async def fareyn(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    u["balance"] += 999999
    await message.answer("+999999 FRN")

# --- СТАВКИ (МНОГО В ОДНОМ СООБЩЕНИИ) ---
BET_RE = re.compile(r'(\d+)\s+((\d+)|(\d+-\d+)|([кч]))', re.IGNORECASE)

@dp.message_handler(lambda m: BET_RE.findall(m.text))
async def bets(message: types.Message):
    uid = message.from_user.id
    cid = message.chat.id
    user = get_user(uid, message.from_user.full_name)

    if cid not in active_rounds:
        active_rounds[cid] = {"start_time": time.time(), "bets": []}

    rnd = active_rounds[cid]
    matches = BET_RE.findall(message.text)

    responses = []

    for m in matches:
        amount = int(m[0])
        target = m[1].lower()

        if user["balance"] < amount:
            responses.append("не хватает денег")
            continue

        count = sum(1 for b in rnd["bets"] if b["uid"] == uid)
        if count >= MAX_BETS_PER_USER:
            responses.append("лимит 100 ставок")
            break

        # тип
        if m[2]:
            if not (0 <= int(target) <= 36):
                responses.append(f"{target} нельзя")
                continue
            b_type = "число"
        elif m[3]:
            b_type = "диапазон"
        else:
            b_type = "цвет"

        user["balance"] -= amount

        rnd["bets"].append({
            "uid": uid,
            "name": user["name"],
            "amt": amount,
            "target": target,
            "type": b_type
        })

        responses.append(f"ставка {amount} на {target} принята")

    await message.answer("\n".join(responses))

# --- ГО ---
@dp.message_handler(lambda m: m.text.lower() == "го")
async def go(message: types.Message):
    cid = message.chat.id

    if cid not in active_rounds or not active_rounds[cid]["bets"]:
        return await message.answer("нет ставок")

    rnd = active_rounds[cid]

    if time.time() - rnd["start_time"] < ROUND_COOLDOWN:
        return await message.answer("жди")

    msg = await message.answer("крутим...")
    await asyncio.sleep(RESULT_PAUSE)

    try:
        await bot.delete_message(cid, msg.message_id)
    except MessageToDeleteNotFound:
        pass

    win = random.randint(0, 36)
    disp, color = get_num_data(win)

    await message.answer(f"выпало {disp}")

    winners = []

    for b in rnd["bets"]:
        payout = 0

        if b["type"] == "число" and int(b["target"]) == win:
            payout = b["amt"] * 30
        elif b["type"] == "цвет" and b["target"] == color:
            payout = b["amt"] * 2
        elif b["type"] == "диапазон":
            try:
                l, h = map(int, b["target"].split("-"))
                if l <= win <= h:
                    payout = b["amt"] * 2
            except:
                pass

        if payout:
            users[b["uid"]]["balance"] += payout
            winners.append(f"{b['name']} +{payout}")

    await message.answer("\n".join(winners) if winners else "никто не выиграл")

    del active_rounds[cid]

# --- СТАРТ ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
