import random
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from sqlalchemy import select
from database.db import get_db
from database.models import User, Lottery, LotteryEntry, PointsHistory
from bot.config import ADMIN_IDS

async def lottery_info(msg: types.Message):
    """Показать информацию о текущем активном розыгрыше"""
    async for session in get_db():
        lottery = await session.scalar(
            select(Lottery).where(Lottery.is_active == True).order_by(Lottery.created_at.desc()).limit(1)
        )
        if not lottery:
            await msg.answer("🎟 Сейчас нет активных розыгрышей.")
            return

        entries_count = await session.scalar(
            select(LotteryEntry).where(LotteryEntry.lottery_id == lottery.id)
        )
        total_tickets = sum(e.tickets for e in entries_count) if entries_count else 0

        text = f"""
🎟 <b>Розыгрыш: {lottery.name}</b>
Стоимость билета: {lottery.ticket_cost} баллов
Призовой фонд: {lottery.prize_pool}
Всего куплено билетов: {total_tickets}
        """
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎟 Купить билет", callback_data="buy_lottery_ticket"))
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)

async def buy_lottery_ticket(call: types.CallbackQuery):
    """Покупка билета розыгрыша"""
    async for session in get_db():
        user = await session.get(User, call.from_user.id)
        lottery = await session.scalar(
            select(Lottery).where(Lottery.is_active == True).order_by(Lottery.created_at.desc()).limit(1)
        )
        if not lottery:
            await call.answer("Нет активного розыгрыша", show_alert=True)
            return

        if user.points < lottery.ticket_cost:
            await call.answer(f"Недостаточно баллов (нужно {lottery.ticket_cost})", show_alert=True)
            return

        user.points -= lottery.ticket_cost
        session.add(PointsHistory(user_id=user.id, points=-lottery.ticket_cost, reason=f"Покупка билета ({lottery.name})"))

        # Добавляем или увеличиваем билеты
        entry = await session.scalar(
            select(LotteryEntry).where(
                LotteryEntry.user_id == user.id,
                LotteryEntry.lottery_id == lottery.id
            )
        )
        if entry:
            entry.tickets += 1
        else:
            entry = LotteryEntry(user_id=user.id, lottery_id=lottery.id, tickets=1)
            session.add(entry)

        await session.commit()
        await call.answer("Билет куплен!", show_alert=True)
        await lottery_info(call.message)

async def draw_winner_cmd(msg: types.Message):
    """Админская команда: провести розыгрыш вручную"""
    if msg.from_user.id not in ADMIN_IDS:
        return

    async for session in get_db():
        lottery = await session.scalar(
            select(Lottery).where(Lottery.is_active == True).order_by(Lottery.created_at.desc()).limit(1)
        )
        if not lottery:
            await msg.answer("Нет активного розыгрыша")
            return

        entries = await session.execute(
            select(LotteryEntry).where(LotteryEntry.lottery_id == lottery.id)
        )
        entries = entries.scalars().all()
        if not entries:
            await msg.answer("Никто не купил билеты")
            return

        # Взвешенный выбор
        users = [e.user_id for e in entries for _ in range(e.tickets)]
        winner_id = random.choice(users)
        winner = await session.get(User, winner_id)

        lottery.winner_id = winner_id
        lottery.is_active = False

        await session.commit()

        await msg.answer(f"🏆 Победитель розыгрыша «{lottery.name}»: {winner.full_name} (@{winner.username})")

        # Оповещение победителя
        try:
            await msg.bot.send_message(winner_id, f"🎉 Поздравляем! Ты выиграл в розыгрыше «{lottery.name}»!")
        except:
            pass

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(lottery_info, Command("lottery"))
    dp.register_callback_query_handler(lottery_info, text="lottery_info")
    dp.register_callback_query_handler(buy_lottery_ticket, text="buy_lottery_ticket")
    dp.register_message_handler(draw_winner_cmd, Command("draw"))
