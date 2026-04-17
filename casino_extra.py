from aiogram import types

bets = []

def cancel_user_bets(bets_list, user_id):
    return [b for b in bets_list if b["user"] != user_id]


async def cancel_handler(msg: types.Message, bets_list):
    user_id = msg.from_user.id

    before = len(bets_list)
    bets_list[:] = cancel_user_bets(bets_list, user_id)
    removed = before - len(bets_list)

    await msg.answer(f"❌ Отменено ставок: {removed}")
