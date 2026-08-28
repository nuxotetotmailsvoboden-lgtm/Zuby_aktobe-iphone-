import asyncio
import random
from celery_app.celery import init_celery
from database.db import AsyncSessionLocal
from database.models import Lottery, LotteryEntry, User
from bot.config import BOT_TOKEN, CHANNEL_ID
from aiogram import Bot

app = init_celery()

async def _draw_lottery_winners():
    """Асинхронная логика розыгрыша"""
    async with AsyncSessionLocal() as session:
        # Ищем все активные розыгрыши, у которых истек срок
        from sqlalchemy import select
        lotteries = await session.execute(
            select(Lottery).where(Lottery.is_active == True)
        )
        lotteries = lotteries.scalars().all()

        bot = Bot(token=BOT_TOKEN)

        for lottery in lotteries:
            entries = await session.execute(
                select(LotteryEntry).where(LotteryEntry.lottery_id == lottery.id)
            )
            entries = entries.scalars().all()

            if not entries:
                continue

            # Взвешенный выбор победителя
            users_pool = []
            for e in entries:
                users_pool.extend([e.user_id] * e.tickets)

            winner_id = random.choice(users_pool)
            winner = await session.get(User, winner_id)

            lottery.winner_id = winner_id
            lottery.is_active = False
            await session.commit()

            # Отправка сообщения в канал
            try:
                await bot.send_message(
                    CHANNEL_ID,
                    f"🏆 <b>Розыгрыш «{lottery.name}» завершён!</b>\n"
                    f"Победитель: {winner.full_name} (@{winner.username})\n"
                    f"Приз: {lottery.prize_pool}",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка отправки в канал: {e}")

            # Оповещение победителя
            try:
                await bot.send_message(
                    winner_id,
                    f"🎉 Поздравляем! Вы выиграли в розыгрыше «{lottery.name}»!\n"
                    f"Приз: {lottery.prize_pool}\n"
                    f"С вами свяжется администратор."
                )
            except Exception as e:
                print(f"Ошибка отправки победителю: {e}")

        await bot.session.close()

@app.task(name='celery_app.tasks.draw_lottery_winners')
def draw_lottery_winners():
    """Синхронная обёртка для Celery"""
    asyncio.run(_draw_lottery_winners())
