import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
import logging

from config import settings
from services.discount import DiscountEngine
from services.antifraud import AntiFraudService
from db.base import async_session
from db.models import Spin, User
from sqlalchemy import select
from keyboards.wheel import get_wheel_keyboard, get_wheel_result_keyboard
from keyboards.main_menu import get_back_keyboard

logger = logging.getLogger(__name__)
router = Router(name="wheel")


BASE_CHANCES = {
    0: 55.0,
    1: 20.0,
    2: 10.0,
    3: 7.0,
    5: 4.0,
    10: 2.0,
    20: 0.8,
    30: 0.15,
    50: 0.04,
    100: 0.01,
}

WHEEL_SECTORS = [
    (0, "0%"), (1, "1%"), (2, "2%"), (3, "3%"), (5, "5%"),
    (10, "10%"), (20, "20%"), (30, "30%"), (50, "50%"), (100, "100%"),
]


async def can_spin(telegram_id: int) -> bool:
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"wheel_cooldown:{telegram_id}"
        exists = await redis.exists(key)
        await redis.close()
        return not exists
    except Exception as e:
        logger.error(f"Redis error in can_spin: {e}")
        return True  # Если Redis недоступен — разрешаем крутить


async def set_spin_cooldown(telegram_id: int):
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"wheel_cooldown:{telegram_id}"
        await redis.setex(key, settings.WHEEL_COOLDOWN_HOURS * 3600, "1")
        await redis.close()
    except Exception as e:
        logger.error(f"Redis error in set_spin_cooldown: {e}")


async def get_spin_cooldown_remaining(telegram_id: int) -> int:
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"wheel_cooldown:{telegram_id}"
        ttl = await redis.ttl(key)
        await redis.close()
        return max(ttl, 0)
    except:
        return 0


@router.callback_query(F.data == "wheel_spin")
async def spin_wheel(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    # Проверка кулдауна
    if not await can_spin(telegram_id):
        remaining = await get_spin_cooldown_remaining(telegram_id)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        current_discount = await DiscountEngine.get_available_discount(telegram_id)

        await callback.message.edit_text(
            f"⏳ <b>Колесо отдыхает!</b>\n\n"
            f"Следующая попытка через: <b>{hours} ч. {minutes} мин.</b>\n\n"
            f"💎 Текущая скидка: <b>{current_discount}%</b>",
            parse_mode="HTML",
            reply_markup=get_wheel_keyboard()
        )
        return

    # Анимация
    await callback.message.edit_text(
        "🎰 <b>Колесо крутится...</b>\n\n🎡 🎡 🎡",
        parse_mode="HTML"
    )
    await asyncio.sleep(1.5)

    # Получаем fraud multiplier
    try:
        multiplier = await AntiFraudService.get_multiplier(telegram_id)
    except:
        multiplier = 1.0  # Если ошибка — считаем пользователя нормальным

    # Корректируем шансы
    adjusted_chances = {}
    total_adjusted = 0
    for prize, prob in BASE_CHANCES.items():
        adjusted = prob * multiplier
        adjusted_chances[prize] = adjusted
        total_adjusted += adjusted
    adjusted_chances[0] += 100 - total_adjusted

    # Выбираем приз
    prizes = list(adjusted_chances.keys())
    probs = list(adjusted_chances.values())
    prob_sum = sum(probs)
    probs = [p / prob_sum for p in probs]
    result = random.choices(prizes, weights=probs, k=1)[0]

    # Сохраняем вращение в БД
    try:
        async with async_session() as session:
            spin = Spin(user_id=telegram_id, prize=result)
            session.add(spin)
            await session.commit()
    except Exception as e:
        logger.error(f"Ошибка сохранения вращения: {e}")

    # Устанавливаем кулдаун
    await set_spin_cooldown(telegram_id)

    # Начисляем скидку если выиграл
    if result > 0:
        try:
            await DiscountEngine.add_discount(
                user_id=telegram_id,
                amount=float(result),
                source="wheel",
                lifetime_days=40,
            )
        except Exception as e:
            logger.error(f"Ошибка начисления скидки: {e}")

    current_discount = await DiscountEngine.get_available_discount(telegram_id)

    # Формируем результат
    if result == 0:
        result_text = (
            f"🎰 <b>РЕЗУЛЬТАТ ВРАЩЕНИЯ</b>\n\n"
            f"😔 К сожалению, вы ничего не выиграли.\n"
            f"Попробуйте ещё раз завтра!\n\n"
            f"💎 Текущая скидка: <b>{current_discount}%</b>"
        )
    elif result >= 50:
        result_text = (
            f"🎰 <b>РЕЗУЛЬТАТ ВРАЩЕНИЯ</b>\n\n"
            f"🎉 <b>ДЖЕКПОТ!!!</b>\n\n"
            f"🏆 Вы выиграли скидку <b>{result}%</b>!\n\n"
            f"💎 Текущая скидка: <b>{current_discount}%</b>\n\n"
            f"Скидка активна 40 дней."
        )
    elif result >= 20:
        result_text = (
            f"🎰 <b>РЕЗУЛЬТАТ ВРАЩЕНИЯ</b>\n\n"
            f"🔥 <b>ОТЛИЧНЫЙ ВЫИГРЫШ!</b>\n\n"
            f"🏆 Вы выиграли скидку <b>{result}%</b>!\n\n"
            f"💎 Текущая скидка: <b>{current_discount}%</b>"
        )
    else:
        result_text = (
            f"🎰 <b>РЕЗУЛЬТАТ ВРАЩЕНИЯ</b>\n\n"
            f"🎁 Вы выиграли скидку <b>{result}%</b>!\n\n"
            f"💎 Текущая скидка: <b>{current_discount}%</b>"
        )

    await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=get_wheel_result_keyboard())


@router.callback_query(F.data == "wheel_history")
async def show_wheel_history(callback: CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Spin).where(Spin.user_id == telegram_id).order_by(Spin.created_at.desc()).limit(20)
            )
            spins = result.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        spins = []

    if not spins:
        text = "📊 <b>ИСТОРИЯ ВРАЩЕНИЙ</b>\n\n<i>Вы ещё не крутили колесо!</i>"
    else:
        text = f"📊 <b>ИСТОРИЯ ВРАЩЕНИЙ</b>\n\nВсего вращений: <b>{len(spins)}</b>\n"
        total_win = sum(s.prize for s in spins)
        text += f"Суммарный выигрыш: <b>{total_win}%</b>\n"
        wins = [s for s in spins if s.prize > 0]
        text += f"Выигрышных: <b>{len(wins)}</b>\n\n<b>Последние вращения:</b>\n"
        for s in spins[:10]:
            emoji = "🎉" if s.prize >= 10 else "🎁" if s.prize > 0 else "😔"
            date_str = s.created_at.strftime("%d.%m.%Y %H:%M")
            text += f"{emoji} {date_str} — <b>{s.prize}%</b>\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_keyboard("menu_wheel"))


@router.callback_query(F.data == "wheel_cooldown")
async def show_cooldown_info(callback: CallbackQuery):
    await callback.answer("⏳ Колесо можно крутить 1 раз в 24 часа", show_alert=True)
