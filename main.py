import asyncio
import random
import re
import time
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageToDeleteNotFound

# Конфигурационные параметры
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
ROUND_COOLDOWN = 15  # Секунд до возможности запуска
RESULT_PAUSE = 2     # Пауза перед выводом результата
MAX_BETS_PER_USER = 100

# Инициализация бота и диспетчера на aiogram 2.25.1
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Хранилище данных (в памяти для демонстрации)
# users: {user_id: {'balance': int, 'name': str, 'used_best': bool}}
users = {}
# active_rounds: {chat_id: {'start_time': float, 'bets':}}
active_rounds = {}

# Математические константы рулетки
RED_NUMBERS = {
    1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36
}
BLACK_NUMBERS = {
    2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35
}

def get_user(user_id, full_name):
    """Инициализация или получение данных пользователя."""
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'name': full_name,
            'used_best': False
        }
    return users[user_id]

def get_number_color_emoji(n):
    """Возвращает число с соответствующим эмодзи цвета."""
    if n == 0:
        return f"🟢 {n}"
    return f"🔴 {n}" if n in RED_NUMBERS else f"⚫ {n}"

def get_number_color_type(n):
    """Возвращает тип цвета для логики выигрыша (к/ч)."""
    if n == 0:
        return "зеро"
    return "к" if n in RED_NUMBERS else "ч"

# --- Обработка промокодов ---

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

# --- Логика обработки ставок ---

# Регулярное выражение для парсинга форматов: "100 9", "100 9-10", "100 к"
# Группы: 1-сумма, 2-цель, 3-число, 4-диапазон, 5-цвет
BET_PATTERN = re.compile(r'^(\d+)\s+((\d+)|(\d+-\d+)|([кч]))$', re.IGNORECASE)

@dp.message_handler(lambda msg: BET_PATTERN.match(msg.text))
async def handle_bet(message: types.Message):
    match = BET_PATTERN.match(message.text)
    amount = int(match.group(1))
    target = match.group(2).lower()
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    user = get_user(user_id, message.from_user.full_name)
    
    # Проверка баланса
    if user['balance'] < amount:
        await message.answer("не хватает денег")
        return

    # Инициализация раунда
    if chat_id not in active_rounds:
        active_rounds[chat_id] = {
            'start_time': time.time(),
            'bets':
        }
    
    current_round = active_rounds[chat_id]
    
    # Проверка лимита в 100 ставок
    user_bets_count = sum(1 for b in current_round['bets'] if b['user_id'] == user_id)
    if user_bets_count >= MAX_BETS_PER_USER:
        await message.answer("Максимум 100 ставок за один раунд на одного игрока!")
        return

    # Регистрация ставки
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

# --- Запуск раунда и определение победителей ---

@dp.message_handler(commands=['го'])
async def cmd_go(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id not in active_rounds or not active_rounds[chat_id]['bets']:
        await message.answer("Ставок еще нет! Сделайте первую ставку.")
        return
    
    current_round = active_rounds[chat_id]
    elapsed = time.time() - current_round['start_time']
    
    # Проверка таймера (15 секунд)
    if elapsed < ROUND_COOLDOWN:
        remaining = int(ROUND_COOLDOWN - elapsed)
        await message.answer(f"осталось {remaining} сек")
        return

    # Начало игровой анимации
    wait_msg = await message.answer("подождите результаты игры")
    await asyncio.sleep(RESULT_PAUSE)
    
    try:
        await bot.delete_message(chat_id, wait_msg.message_id)
    except MessageToDeleteNotFound:
        pass

    # Генерация выигрышного числа
    win_number = random.randint(0, 36)
    win_color_type = get_number_color_type(win_number)
    win_display = get_number_color_emoji(win_number)

    # 1. Формирование списка всех ставок
    all_bets_report = f"Результат: {win_display}\n\n<b>Список всех ставок:</b>\n"
    for b in current_round['bets']:
        all_bets_report += f"{b['user_name']} — {b['amount']} — {b['target']}\n"
    
    await message.answer(all_bets_report)

    # 2. Определение выигрышных ставок
    winning_bets_report = "<b>Выигрышные ставки:</b>\n"
    winners_found = False
    
    player_stats = {} # {user_id: {name, total_bet, bets_count, total_win}}

    for b in current_round['bets']:
        u_id = b['user_id']
        if u_id not in player_stats:
            player_stats[u_id] = {
                'name': b['user_name'],
                'total_bet': 0,
                'bets_count': 0,
                'total_win': 0
            }
        
        stats = player_stats[u_id]
        stats['total_bet'] += b['amount']
        stats['bets_count'] += 1
        
        is_winner = False
        payout = 0
        
        if b['type'] == 'число':
            if int(b['target']) == win_number:
                is_winner = True
                payout = b['amount'] * 30
        elif b['type'] == 'диапазон':
            start, end = map(int, b['target'].split('-'))
            if start <= win_number <= end:
                is_winner = True
                payout = b['amount'] * 2
        elif b['type'] == 'цвет':
            if b['target'] == win_color_type:
                is_winner = True
                payout = b['amount'] * 2
        
        if is_winner:
            stats['total_win'] += payout
            users[u_id]['balance'] += payout
            winning_bets_report += f"✅ {b['user_name']} — {payout} FRN\n"
            winners_found = True

    if not winners_found:
        winning_bets_report += "Нет выигрышных ставок в этом раунде."
    
    await message.answer(winning_bets_report)

    # 3. Итоговая часть
    final_summary = "<b>Итоги раунда:</b>\n"
    for u_id, s in player_stats.items():
        final_summary += (
            f"👤 {s['name']}\n"
            f"💰 Ставка: {s['total_bet']} FRN\n"
            f"📊 Кол-во ставок: {s['bets_count']}\n"
            f"🏆 Выигрыш: {s['total_win']} FRN\n\n"
        )
    
    await message.answer(final_summary)

    # Сброс раунда в этом чате
    del active_rounds[chat_id]

if __name__ == '__main__':
    print("Бот Fareyn's Casino запущен!")
    executor.start_polling(dp, skip_updates=True)
