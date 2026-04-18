import asyncio
import random
import re
import time
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageToDeleteNotFound

# --- НАСТРОЙКИ ---
# Замените токен на ваш, полученный от @BotFather
API_TOKEN = 'ВАШ_ТОКЕН_ЗДЕСЬ'
ROUND_COOLDOWN = 15  # Время ожидания перед "го" (в секундах)
RESULT_PAUSE = 2     # Пауза "подождите результаты" (в секундах)
MAX_BETS_PER_USER = 100

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Базы данных (в оперативной памяти)
users = {}          # {user_id: {balance, name, used_best}}
active_rounds = {}  # {chat_id: {start_time, bets:}}

# Определение цветов рулетки согласно стандарту
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

def get_user(user_id, full_name):
    if user_id not in users:
        users[user_id] = {'balance': 0, 'name': full_name, 'used_best': False}
    return users[user_id]

def get_num_data(n):
    if n == 0: return "🟢 0", "зеро"
    if n in RED_NUMBERS: return f"🔴 {n}", "к"
    return f"⚫ {n}", "ч"

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

# --- ПЕРЕВОД ВАЛЮТЫ ---
@dp.message_handler(regexp=r'^перевод\s+(\d+)\s+(\d+)$')
async def transfer_money(message: types.Message):
    match = re.match(r'^перевод\s+(\d+)\s+(\d+)$', message.text)
    target_id, amount = int(match.group(1)), int(match.group(2))
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

# --- СИСТЕМА СТАВОК ---
# Регулярное выражение для парсинга: "100 9", "100 9-10", "100 к"
BET_PATTERN = re.compile(r'^(\d+)\s+((\d+)|(\d+-\d+)|([кч]))$', re.IGNORECASE)

@dp.message_handler(lambda m: BET_PATTERN.match(m.text))
async def handle_bet(message: types.Message):
    match = BET_PATTERN.match(message.text)
    amount = int(match.group(1))
    target = match.group(2).lower()
    uid, cid = message.from_user.id, message.chat.id
    user = get_user(uid, message.from_user.full_name)

    if user['balance'] < amount:
        await message.answer("не хватает денег")
        return

    # Инициализация раунда с исправленным синтаксисом
    if cid not in active_rounds:
        active_rounds[cid] = {'start_time': time.time(), 'bets':}
    
    round_data = active_rounds[cid]
    user_bets_count = sum(1 for b in round_data['bets'] if b['uid'] == uid)
    
    if user_bets_count >= MAX_BETS_PER_USER:
        await message.answer("Максимум 100 ставок за раунд!")
        return

    # Классификация типа ставки
    if match.group(3): b_type = 'число'
    elif match.group(4): b_type = 'диапазон'
    else: b_type = 'цвет'

    user['balance'] -= amount
    round_data['bets'].append({
        'uid': uid, 'name': user['name'], 'amt': amount, 
        'target': target, 'type': b_type
    })
    await message.answer(f"ставка {amount} на {target} принята")

# --- ЗАПУСК ИГРЫ ---
@dp.message_handler(commands=['го'])
async def cmd_go(message: types.Message):
    cid = message.chat.id
    if cid not in active_rounds or not active_rounds[cid]['bets']:
        await message.answer("Ставок еще нет! Сделайте первую ставку.")
        return

    rnd = active_rounds[cid]
    elapsed = time.time() - rnd['start_time']
    
    if elapsed < ROUND_COOLDOWN:
        await message.answer(f"осталось {int(ROUND_COOLDOWN - elapsed)} сек")
        return

    # Начало анимации
    wait_msg = await message.answer("подождите результаты игры")
    await asyncio.sleep(RESULT_PAUSE)
    try:
        await bot.delete_message(cid, wait_msg.message_id)
    except Exception:
        pass

    # Определение результата
    win_num = random.randint(0, 36)
    win_display, win_color_code = get_num_data(win_num)

    # 1. Отчет обо всех ставках
    report = f"Результат: {win_display}\n\n<b>Список всех ставок:</b>\n"
    for b in rnd['bets']:
        report += f"{b['name']} — {b['amt']} — {b['target']} ({b['type']})\n"
    await message.answer(report)

    # 2. Список победителей и расчет выигрышей
    winners_text = "<b>Выигрышные ставки:</b>\n"
    player_stats = {} # {uid: {name, total_bet, count, win, types: set}}
    any_winner = False

    for b in rnd['bets']:
        uid = b['uid']
        if uid not in player_stats:
            player_stats[uid] = {'name': b['name'], 'total_bet': 0, 'count': 0, 'win': 0, 'types': set()}
        
        ps = player_stats[uid]
        ps['total_bet'] += b['amt']
        ps['count'] += 1
        ps['types'].add(b['target'])
        
        payout = 0
        if b['type'] == 'число' and int(b['target']) == win_num:
            payout = b['amt'] * 30
        elif b['type'] == 'цвет' and b['target'] == win_color_code:
            payout = b['amt'] * 2
        elif b['type'] == 'диапазон':
            low, high = map(int, b['target'].split('-'))
            if low <= win_num <= high: payout = b['amt'] * 2
        
        if payout > 0:
            ps['win'] += payout
            users[uid]['balance'] += payout
            winners_text += f"✅ {b['name']} получил {payout} FRN\n"
            any_winner = True

    if not any_winner: winners_text += "В этом раунде никто не выиграл."
    await message.answer(winners_text)

    # 3. Финальный итог
    summary = "<b>Итоговая часть:</b>\n"
    for uid, s in player_stats.items():
        all_types = ", ".join(list(s['types']))
        summary += (f"👤 {s['name']}\n💰 Общая ставка: {s['total_bet']} | Типы: {all_types}\n"
                   f"📊 Сделано ставок: {s['count']}\n🏆 Итоговый выигрыш: {s['win']} FRN\n\n")
    
    await message.answer(summary)
    
    # Очистка данных раунда
    del active_rounds[cid]

if __name__ == '__main__':
    print("Fareyn's Casino Bot запущен...")
    executor.start_polling(dp, skip_updates=True)
