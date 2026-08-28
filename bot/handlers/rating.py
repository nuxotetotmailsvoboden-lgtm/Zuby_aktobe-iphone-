from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database.db import get_db
from database.models import User

async def rating_cmd(msg: types.Message):
    """Топ-10 пользователей по баллам"""
    async for session in get_db():
        top_users = (await session.execute(
            select(User).order_by(User.points.desc()).limit(10)
        )).scalars().all()

        text = "🏆 <b>Рейтинг игроков</b>\n\n"
        for i, user in enumerate(top_users, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            name = user.full_name or user.username or "Без имени"
            text += f"{medal} {name} — {user.points} баллов (Lv.{user.level})\n"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))

        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

async def rating_callback(call: types.CallbackQuery):
    """Обработка кнопки Рейтинг из меню"""
    await rating_cmd(call.message)
    await call.answer()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(rating_cmd, Command("rating"))
    dp.register_callback_query_handler(rating_callback, text="rating")
