import re
import secrets
from datetime import datetime
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy import select, func
from database.db import get_db
from database.models import User, PointsHistory
from bot.keyboards.inline import main_menu_kb
from bot.utils.validators import validate_full_name, validate_phone
from bot.middlewares.antifraud import check_registration_limit

class Registration(StatesGroup):
    full_name = State()
    phone = State()
    instagram = State()

async def start_cmd(msg: types.Message, state: FSMContext):
    """Точка входа: /start. Проверка регистрации и запуск анкеты"""
    if not await check_registration_limit(msg.from_user.id):
        await msg.answer("⛔ Превышен лимит регистраций. Попробуйте позже.")
        return

    args = msg.get_args()
    referrer_id = int(args) if args and args.isdigit() else None

    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        if not user:
            # Новый пользователь
            referral_code = secrets.token_urlsafe(8)
            user = User(
                id=msg.from_user.id,
                username=msg.from_user.username,
                referral_code=referral_code,
                referrer_id=referrer_id
            )
            session.add(user)
            await session.commit()
            await Registration.full_name.set()
            await msg.answer(
                "👋 Добро пожаловать! Давай заполним анкету.\n\n"
                "Введи свои <b>Имя и Фамилию</b> (только буквы, пробел или дефис):",
                parse_mode="HTML"
            )
        else:
            # Существующий пользователь
            if not user.full_name or not user.phone:
                await Registration.full_name.set()
                await msg.answer("Пожалуйста, заверши регистрацию. Введи Имя и Фамилию:")
            else:
                await msg.answer("С возвращением!", reply_markup=main_menu_kb())

async def process_full_name(msg: types.Message, state: FSMContext):
    """Валидация имени и фамилии"""
    if not validate_full_name(msg.text):
        await msg.answer("❌ Некорректное имя. Используй только буквы, пробел или дефис (2-50 символов). Попробуй снова:")
        return

    await state.update_data(full_name=msg.text.strip())
    await Registration.next()
    await msg.answer("📞 Введи номер телефона в формате <b>+7XXXXXXXXXX</b> (например +71234567890):", parse_mode="HTML")

async def process_phone(msg: types.Message, state: FSMContext):
    """Валидация телефона и проверка уникальности"""
    phone = msg.text.strip()
    if not validate_phone(phone):
        await msg.answer("❌ Неверный формат. Введи номер строго как +7XXXXXXXXXX (12 символов).")
        return

    async for session in get_db():
        existing = await session.scalar(
            select(func.count()).where(User.phone == phone)
        )
        if existing > 0:
            await msg.answer("⚠️ Этот номер телефона уже зарегистрирован. Введи другой.")
            return

        await state.update_data(phone=phone)
        await Registration.next()
        await msg.answer("📷 Введи свой Instagram (например @username):")

async def process_instagram(msg: types.Message, state: FSMContext):
    """Завершение регистрации, начисление бонусов рефереру"""
    instagram = msg.text.strip()
    data = await state.get_data()
    full_name = data.get("full_name")
    phone = data.get("phone")

    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        user.full_name = full_name
        user.phone = phone
        user.instagram = instagram

        # Начисление бонуса рефереру (1 уровень)
        if user.referrer_id and user.referrer_id != user.id:
            referrer = await session.get(User, user.referrer_id)
            if referrer:
                referrer.points += 100
                session.add(PointsHistory(user_id=referrer.id, points=100, reason="Реферал 1 уровня"))

                # Бонус рефереру 2 уровня
                if referrer.referrer_id:
                    ref2 = await session.get(User, referrer.referrer_id)
                    if ref2:
                        ref2.points += 50
                        session.add(PointsHistory(user_id=ref2.id, points=50, reason="Реферал 2 уровня"))

        await session.commit()

    await state.finish()
    await msg.answer(
        "✅ Регистрация завершена! Теперь ты можешь пользоваться ботом.\n"
        "Твоя реферальная ссылка уже активна – приглашай друзей и получай баллы!",
        reply_markup=main_menu_kb()
    )

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_cmd, CommandStart(), state="*")
    dp.register_message_handler(process_full_name, state=Registration.full_name)
    dp.register_message_handler(process_phone, state=Registration.phone)
    dp.register_message_handler(process_instagram, state=Registration.instagram)
