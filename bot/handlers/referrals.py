from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from sqlalchemy import select, func
from database.db import get_db
from database.models import User

async def my_ref_link(msg: types.Message):
    """Показать реферальную ссылку и статистику"""
    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        if not user:
            await msg.answer("Сначала зарегистрируйся через /start")
            return

        bot = await msg.bot.get_me()
        link = f"https://t.me/{bot.username}?start={msg.from_user.id}"

        count = await session.scalar(
            select(func.count()).where(User.referrer_id == user.id)
        )

        await msg.answer(
            f"🔗 Твоя реферальная ссылка:\n{link}\n\n"
            f"👥 Приглашено: {count} чел.\n"
            f"💰 Твой баланс: {user.points} баллов"
        )

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(my_ref_link, Command("ref"))
