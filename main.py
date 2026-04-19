import asyncio
import random
import re
import time
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageToDeleteNotFound

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = 'ВАШ_ТОКЕН_ЗДЕСЬ'
ROUND_COOLDOWN = 15
RESULT_PAUSE = 2
MAX_BETS_PER_USER = 100
DAILY_BONUS_AMOUNT = 2500

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Базы данных в памяти
users = {}          # {user_id: {balance, name, used_best, last_bonus}}
active_rounds = {}  # {chat_id: {start_time, bets}}

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

def get_user(user_id, full_name):
    if user_id not in users:
        users[user_id] = {
            'balance': 0, 
            'name': full_name, 
            'used_best': False,
            'last_bonus': 0
        }
    return users[user_id]

def get_num_data(n):
    if n == 0: return "🟢 0", "зеро"
    if n in RED_NUMBERS: return f"🔴 {n}", "к"
    return f"⚫ {n}", "ч"

# --- ЕЖЕДНЕВНЫЙ БОНУС ---
@dp.message_handler(lambda m: m.text.lower() == "бонус")
async def cmd_bonus(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    now = time.time()
    # Проверка 24 часов (86400 секунд)
    if now - u['last_bonus'] >= 86400:
        u['balance'] += DAILY_BONUS_AMOUNT
        u['last_bonus'] = now
        await message.answer(f"🎁 Вы получили ежедневный бонус {DAILY_BONUS_AMOUNT} FRN!")
    else:
        rem = int(86400 - (now - u['last_bonus']))
        hours = rem // 3600
        mins = (rem % 3600) // 60
        await message.answer(f"⏳ Бонус будет доступен через {hours}ч {mins}м.")

# --- ПРОМОКОДЫ ---
@dp.message_handler(lambda m: m.text == "Лучший")
async def promo_best(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    if u['used_best']:
        await message.answer("Вы уже использовали этот промокод.")
    else:
        u['balance'] += 5555
        u['used_best'] = True
        await message.answer("Код 'Лучший' принят! +5555 FRN")

@dp.message_handler(lambda m: m.text == "Фарейн")
async def promo_fareyn(message: types.Message):
    u = get_user(message.from_user.id, message.from_user.full_name)
    u['balance'] += 999999
    await message.answer("Код 'Фарейн' принят! +999999 FRN")

# --- ПЕРЕВОД (КОМАНДА "П") ---
@dp.message_handler(regexp=r'^п\s+(\d+)\s+(\d+)$')
async def transfer_money(message: types.Message):
    match = re.match(r'^п\s+(\d+)\s+(\d+)$', message.text)
    target_id, amount = int(match.group(1)), int(match.group(2))
    sender = get_user(message.from_user.id, message.from_user.full_name)
    
    if sender['balance'] < amount:
        await message.answer("не хватает денег")
        return
    
    if target_id not in users:
        await message.answer("Пользователь не найден.")
        return

    sender['balance'] -= amount
    users[target_id]['balance'] += amount
    await message.answer(f"Перевод {amount} FRN для {users[target_id]['name']} выполнен.")

# --- СИСТЕМА СТАВОК ---
BET_RE = re.compile(r'^(\d+)\s+((\d+)|(\d+-\d+)|([кч]))$', re.IGNORECASE)

@dp.message_handler(lambda m: BET_RE.match(m.text))
async def place_bet(message: types.Message):
    match = BET_RE.match(message.text)
    amt, target = int(match.group(1)), match.group(2).lower()
    uid, cid = message.from_user.id, message.chat.id
    u = get_user(uid, message.from_user.full_name)

    if u['balance'] < amt:
        await message.answer("не хватает денег")
        return

    if cid not in active_rounds:
        active_rounds[cid] = {'start_time': time.time(), 'bets':}
    
    rnd = active_rounds[cid]
    if sum(1 for b in rnd['bets'] if b['uid'] == uid) >= MAX_BETS_PER_USER:
        await message.answer("Лимит 100 ставок!")
        return

    u['balance'] -= amt
    b_type = 'число' if match.group(3) else ('диапазон' if match.group(4) else 'цвет')
    rnd['bets'].append({'uid': uid, 'name': u['name'], 'amt': amt, 'target': target, 'type': b_type})
    await message.answer(f"ставка {amt} на {target} принята")

# --- ЗАПУСК ---
@dp.message_handler(lambda m: m.text.lower() == "го")
async def cmd_go(message: types.Message):
    cid = message.chat.id
    if cid not in active_rounds or not active_rounds[cid]['bets']:
        await message.answer("Ставок еще нет!")
        return

    rnd = active_rounds[cid]
    elapsed = time.time() - rnd['start_time']
    if elapsed < ROUND_COOLDOWN:
        await message.answer(f"осталось {int(ROUND_COOLDOWN - elapsed)} сек")
        return

    wait_msg = await message.answer("подождите результаты игры")
    await asyncio.sleep(RESULT_PAUSE)
    try: await bot.delete_message(cid, wait_msg.message_id)
    except: pass

    win_num = random.randint(0, 36)
    win_disp, win_clr = get_num_data(win_num)

    # 1. Список всех ставок
    res = f"Результат: {win_disp}\n\n<b>Список всех ставок:</b>\n"
    for b in rnd['bets']:
        res += f"{b['name']} — {b['amt']} — {b['target']}\n"
    await message.answer(res)

    # 2. Победители
    win_res = "<b>Выигрышные ставки:</b>\n"
    stats = {} 
    any_win = False

    for b in rnd['bets']:
        uid = b['uid']
        if uid not in stats: stats[uid] = {'name': b['name'], 'total_bet': 0, 'count': 0, 'win': 0, 'targets':}
        ps = stats[uid]
        ps['total_bet'] += b['amt']
        ps['count'] += 1
        ps['targets'].append(b['target'])
        
        payout = 0
        if b['type'] == 'число' and int(b['target']) == win_num: payout = b['amt'] * 30
        elif b['type'] == 'цвет' and b['target'] == win_clr: payout = b['amt'] * 2
        elif b['type'] == 'диапазон':
            try:
                low, high = map(int, b['target'].split('-'))
                if low <= win_num <= high: payout = b['amt'] * 2
            except: pass
        
        if payout > 0:
            ps['win'] += payout
            users[uid]['balance'] += payout
            win_res += f"✅ {b['name']} выиграл {payout} FRN\n"
            any_winner = True

    if not any_win: win_res += "Нет выигрышей"
    await message.answer(win_res)

    # 3. Итоги
    fin = "<b>Итоги раунда:</b>\n"
    for uid, s in stats.items():
        fin += f"👤 {s['name']} | Ставок: {s['count']} | Выиграл: {s['win']} FRN\n"
    await message.answer(fin)
    del active_rounds[cid]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
