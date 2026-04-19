import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data.json"

# ================== ДАННЫЕ ==================
def load():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, "r", encoding="utf-8"))
    return {}

def save():
    json.dump(users, open(DATA_FILE, "w", encoding="utf-8"))

users = load()

def get_user(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "баланс": 5000,
            "коды": [],
        }
        save()

    return users[uid]

# ================== ИГРА ==================
game = {
    "активна": False,
    "ставки": [],
    "лог": []
}

# ================== СТАРТ ==================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    get_user(m.from_user.id)

    await m.answer(
        "🎰 FARAIN CASINO\n\n"
        "💰 баланс / б\n"
        "🎲 ставка: 500 9 9-20\n"
        "🚀 go — старт раунда\n"
        "🎁 4999 — код\n"
        "💎 farain — бесконечный код\n\n"
        "📌 типы ставок:\n"
        "• число (9)\n"
        "• диапазон (9-20)\n"
        "• чёт / нечёт\n"
        "• красное / чёрное"
    )

# ================== БАЛАНС ==================
@dp.message_handler(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def bal(m: types.Message):
    u = get_user(m.from_user.id)
    await m.answer(f"💰 Баланс: {u['баланс']} FRN")

# ================== КОД 4999 ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "4999")
async def c1(m: types.Message):
    u = get_user(m.from_user.id)

    if "4999" not in u["коды"]:
        u["баланс"] += 4999
        u["коды"].append("4999")
        save()
        await m.answer("🎁 +4999 FRN (одноразовый код)")
    else:
        await m.answer("❌ код уже использован")

# ================== КОД FARAIN ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "farain")
async def c2(m: types.Message):
    u = get_user(m.from_user.id)

    u["баланс"] += 987654
    save()

    await m.answer("💎 +987654 FRN (FARAIN код активирован)")

# ================== СТАВКИ ==================
@dp.message_handler()
async def bet(m: types.Message):
    if not game["активна"]:
        return

    u = get_user(m.from_user.id)
    text = m.text.lower().split()

    try:
        сумма = int(text[0])
        ставки = text[1:]

        for s in ставки:

            if u["баланс"] < сумма:
                await m.answer("❌ недостаточно денег")
                continue

            u["баланс"] -= сумма

            game["ставки"].append({
                "юзер": m.from_user.id,
                "имя": m.from_user.first_name,
                "сумма": сумма,
                "ставка": s
            })

            await m.answer(f"📥 Ставка {сумма} на {s} принята")

        save()

    except:
        pass

# ================== РАУНД ==================
@dp.message_handler(lambda m: m.text and m.text.lower() == "go")
async def go(m: types.Message):

    if game["активна"]:
        await m.answer("⏳ раунд уже идёт")
        return

    game["активна"] = True
    game["ставки"] = []

    await m.answer("🎰 Ставки открыты! 15 секунд...")

    await asyncio.sleep(15)

    число = random.randint(0, 36)

    game["лог"].append(число)
    if len(game["лог"]) > 10:
        game["лог"].pop(0)

    красные = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]

    результаты = []

    for s in game["ставки"]:

        win = False

        # число
        if s["ставка"].isdigit():
            if int(s["ставка"]) == число:
                win = True

        # диапазон
        elif "-" in s["ставка"]:
            a, b = map(int, s["ставка"].split("-"))
            if a <= число <= b:
                win = True

        # чёт / нечёт
        elif s["ставка"] == "чёт" and число % 2 == 0:
            win = True

        elif s["ставка"] == "нечёт" and число % 2 == 1:
            win = True

        # красное / чёрное
        elif s["ставка"] == "красное" and число in красные:
            win = True

        elif s["ставка"] == "чёрное" and число not in красные:
            win = True

        if win:
            награда = s["сумма"] * 2
            u = get_user(s["юзер"])
            u["баланс"] += награда

            результаты.append(
                f"🏆 {s['имя']} выиграл {награда} FRN на {s['ставка']} (число {число})"
            )

    save()

    game["активна"] = False

    await m.answer(
        f"🎰 РЕЗУЛЬТАТ: {число}\n\n"
        + ("\n".join(результаты) if результаты else "❌ победителей нет") +
        f"\n\n📊 последние: {game['лог']}"
    )

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    print("🎰 FARAIN CASINO v4 запущен")
    executor.start_polling(dp, skip_updates=True)
