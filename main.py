import asyncio
import random
import re
import time
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageToDeleteNotFound

# Конфигурационные параметры
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
ROUND_COOLDOWN = 15  
RESULT_PAUSE = 2     
MAX_BETS_PER_USER = 100

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Хранилище данных
# users: {user_id: {'balance': int, 'name': str, 'used_best': bool}}
users = {}
# active_rounds: {chat_id: {'start_time': float, 'bets':}}
active_rounds = {}

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

def get_user(user_id, full_name):
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'name': full_name,
            'used_best': False
        }
    return users[user_id]

def get_number_color_emoji(n):
    if n == 0: return f"🟢 {n}"
    return f"🔴 {n}" if n in RED_NUMBERS else f"⚫ {n}"

def get_number_color_type(n):
    if n == 0: return "зеро"
    return "к" if n in RED_NUMBERS else "ч"

# --- Промокоды ---
@dp.message_handler(lambda msg: msg.text == "Лучший")
async def cmd_promo_best(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.full_name)
    if user['used_best']:
        await message.answer("Вы уже использовали этот промокод.")
        return
    user['balance'] += 5555
    user['used_best'] = True
    await message.answer("Промокод 'Лучший' активирован! +5555 FRN.")

@dp.message_handler(lambda msg: msg.text == "Фарейн")
async def cmd_promo_fareyn(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.full_name)
    user['balance'] += 999999
    await message.answer("Промокод 'Фарейн' активирован! +999999 FRN.")

# --- Перевод валюты ---
@dp.message_handler(regexp=r'^перевод\s+(\d+)\s+(\d+)$')
async def handle_transfer(message: types.Message):
    match = re.match(r'^перевод\s+(\d+)\s+(\d+)$', message.text)
    target_id = int(match.group(1))
    amount = int(match.group(2))
    
    sender = get_user(message.from_user.id, message.from_user.full_name)
    
    if sender['balance'] < amount:
        await message.answer("не хватает денег")
        return
    
    if target_id not in users:
        await message.answer("Пользователь не найден в системе.")
        return

    sender['balance'] -= amount
    users[target_id]['balance'] += amount
    await message.answer(f"Перевод {amount} FRN пользователю {users[target_id]['name']} выполнен.")

# --- Ставки ---
BET_PATTERN = re.compile(r'^(\d+)\s+((\d+)|(\d+-\d+)|([кч]))$', re.IGNORECASE)

@dp.message_handler(lambda msg: BET_PATTERN.match(msg.text))
async def handle_bet(message: types.Message):
    match = BET_PATTERN.match(message.text)
    amount = int(match.group(1))
    target = match.group(2).lower()
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    user = get_user(user_id, message.from_user.full_name)
    
    if user['balance'] < amount:
        await message.answer("не хватает денег")
        return

    if chat_id not in active_rounds:
        active_rounds[chat_id] = {
            'start_time': time.time(),
            'bets':
        }
    
    current_round = active_rounds[chat_id]
    user_bets_count = sum(1 for b in current_round['bets'] if b['user_id'] == user_id)
    
    if user_bets_count >= MAX_BETS_PER_USER:
        await message.answer("Максимум 100 ставок за один раунд!")
        return

    user['balance'] -= amount
    bet_type = 'число' if match.group(3) else ('диапазон' if match.group(4) else 'цвет')
    
    current_round['bets'].append({
        'user_id': user_id,
        'user_name': message.from_user.full_name,
        'amount': amount,
        'target': target,
        'type': bet_type
    })
    await message.answer(f"ставка {amount} на {target} принята")

# --- Запуск ---
@dp.message_handler(commands=['го'])
async def cmd_go(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in active_rounds or not active_rounds[chat_id]['bets']:
        await message.answer("Ставок еще нет!")
        return
    
    current_round = active_rounds[chat_id]
    elapsed = time.time() - current_round['start_time']
    
    if elapsed < ROUND_COOLDOWN:
        await message.answer(f"осталось {int(ROUND_COOLDOWN - elapsed)} сек")
        return

    wait_msg = await message.answer("подождите результаты игры")
    await asyncio.sleep(RESULT_PAUSE)
    try: await bot.delete_message(chat_id, wait_msg.message_id)
    except: pass

    win_number = random.randint(0, 36)
    win_color_type = get_number_color_type(win_number)
    win_display = get_number_color_emoji(win_number)

    report = f"Результат: {win_display}\n\n<b>Все ставки:</b>\n"
    for b in current_round['bets']:
        report += f"{b['user_name']} — {b['amount']} — {b['target']} ({b['type']})\n"
    await message.answer(report)

    win_report = "<b>Выигрыши:</b>\n"
    player_stats = {}
    found_winners = False

    for b in current_round['bets']:
        u_id = b['user_id']
        if u_id not in player_stats:
            player_stats[u_id] = {'name': b['user_name'], 'total_bet': 0, 'count': 0, 'win': 0}
        
        s = player_stats[u_id]
        s['total_bet'] += b['amount']
        s['count'] += 1
        
        payout = 0
        if b['type'] == 'число' and int(b['target']) == win_number:
            payout = b['amount'] * 30
        elif b['type'] == 'диапазон':
            start, end = map(int, b['target'].split('-'))
            if start <= win_number <= end: payout = b['amount'] * 2
        elif b['type'] == 'цвет' and b['target'] == win_color_type:
            payout = b['amount'] * 2
            
        if payout > 0:
            s['win'] += payout
            users[u_id]['balance'] += payout
            win_report += f"✅ {b['user_name']} +{payout} FRN\n"
            found_winners = True

    if not found_winners: win_report += "Нет победителей."
    await message.answer(win_report)

    summary = "<b>Итоги:</b>\n"
    for u_id, s in player_stats.items():
        summary += f"👤 {s['name']} | Ставок: {s['count']} | Итог: {s['win']} FRN\n"
    await message.answer(summary)
    del active_rounds[chat_id]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
