import random
from datetime import datetime, timedelta
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database.db import get_db
from database.models import User, PointsHistory
from bot.utils.decorators import daily_limit

# Таблица уровней: {уровень: необходимый опыт}
LEVELS = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2100,
    8: 2800,
    9: 3600,
    10: 4500,
}

async def profile_cmd(msg: types.Message):
    """Показать профиль пользователя"""
    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        if not user:
            await msg.answer("Сначала зарегистрируйся через /start")
            return

        next_level = user.level + 1
        next_exp = LEVELS.get(next_level, 0)
        progress = (user.experience / next_exp * 100) if next_exp else 100

        text = f"""
🎮 <b>Профиль</b>
👤 {user.full_name}
⭐ Уровень: {user.level} ({user.experience}/{next_exp} опыта, {progress:.1f}%)
💰 Баланс: {user.points} баллов | {user.coins} монет
👥 Рефералов: {len(user.referrals)}
📞 Телефон: {user.phone}
📷 Instagram: {user.instagram}
🔥 Серия дней: {user.streak_days}
        """

        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_bonus"),
            InlineKeyboardButton("🎡 Колесо фортуны", callback_data="wheel"),
            InlineKeyboardButton("📋 Миссии", callback_data="missions"),
            InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"),
            InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile")
        )
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

async def back_to_profile(call: types.CallbackQuery):
    """Кнопка Назад в профиль"""
    await profile_cmd(call.message)
    await call.answer()

async def check_level_up(user: User, session) -> bool:
    """Проверяет, можно ли повысить уровень, и повышает"""
    next_level = user.level + 1
    if next_level in LEVELS and user.experience >= LEVELS[next_level]:
        user.level = next_level
        user.coins += 50 * next_level  # бонус за уровень
        return True
    return False

@daily_limit("daily_bonus", hours=24)
async def daily_bonus(call: types.CallbackQuery):
    """Ежедневный бонус с учётом серии и уровня"""
    async for session in get_db():
        user = await session.get(User, call.from_user.id)
        now = datetime.now()

        # Логика серии
        if user.last_daily_bonus:
            delta = now - user.last_daily_bonus
            if delta.days == 1:
                user.streak_days += 1
            elif delta.days > 1:
                user.streak_days = 1
        else:
            user.streak_days = 1

        # Расчёт бонуса
        base = 50
        streak_bonus = min(user.streak_days * 5, 50)
        level_bonus = (user.level - 1) * 10
        total = base + streak_bonus + level_bonus

        user.points += total
        user.experience += 10
        user.last_daily_bonus = now

        session.add(PointsHistory(
            user_id=user.id,
            points=total,
            reason=f"Ежедневный бонус (день {user.streak_days})"
        ))

        leveled_up = await check_level_up(user, session)
        await session.commit()

        msg = f"🎁 Получено {total} баллов!\n🔥 Серия: {user.streak_days} дней\n📊 Опыт: +10"
        if leveled_up:
            msg += f"\n🎉 Поздравляем! Ты достиг уровня {user.level}!"
        await call.message.edit_text(msg)

async def wheel_fortune(call: types.CallbackQuery):
    """Колесо фортуны (стоимость 10 монет)"""
    async for session in get_db():
        user = await session.get(User, call.from_user.id)
        if user.coins < 10:
            await call.answer("❌ Недостаточно монет (нужно 10)", show_alert=True)
            return

        user.coins -= 10

        prizes = [
            {"name": "100 баллов", "chance": 30, "points": 100},
            {"name": "50 баллов", "chance": 40, "points": 50},
            {"name": "200 баллов", "chance": 15, "points": 200},
            {"name": "500 баллов", "chance": 10, "points": 500},
            {"name": "1000 баллов", "chance": 5, "points": 1000},
        ]
        prize = random.choices(prizes, weights=[p["chance"] for p in prizes])[0]

        user.points += prize["points"]
        user.experience += 15

        session.add(PointsHistory(
            user_id=user.id,
            points=prize["points"],
            reason=f"Колесо фортуны: {prize['name']}"
        ))

        leveled_up = await check_level_up(user, session)
        await session.commit()

        msg = f"🎡 Вы выиграли: {prize['name']}!\n💰 Баланс: {user.points} баллов"
        if leveled_up:
            msg += f"\n🎉 Ты достиг уровня {user.level}!"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🎡 Крутить ещё", callback_data="wheel"))
        kb.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))

        await call.message.edit_text(msg, reply_markup=kb)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(profile_cmd, Command("profile"))
    dp.register_callback_query_handler(back_to_profile, text="back_to_profile")
    dp.register_callback_query_handler(profile_cmd, text="profile")
    dp.register_callback_query_handler(daily_bonus, text="daily_bonus")
    dp.register_callback_query_handler(wheel_fortune, text="wheel")
