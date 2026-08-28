from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from sqlalchemy import select
import logging
import re

from db.base import async_session
from db.models import User, Referral
from states.fsm import RegistrationFSM
from keyboards.registration import get_instagram_check_keyboard, get_instagram_link_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from utils.validators import validate_name, validate_phone, format_phone, generate_ref_code

logger = logging.getLogger(__name__)
router = Router(name="registration")


async def user_exists(telegram_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None


async def phone_exists(phone: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none() is not None


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def is_admin(telegram_id: int) -> bool:
    from config import settings
    return telegram_id in settings.SUPERADMINS or telegram_id in settings.ADMINS


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.clear()
    
    if await user_exists(telegram_id):
        user = await get_user(telegram_id)
        await message.answer(
            f'👋 С возвращением, {user.first_name}!\n\n'
            f'Рады видеть вас снова в нашей стоматологии!',
            reply_markup=get_main_menu_keyboard(is_admin=await is_admin(telegram_id))
        )
        return
    
    args = message.text.split()
    ref_code = None
    
    if len(args) > 1:
        ref_code = args[1]
    elif message.text and "start=" in message.text:
        ref_code = message.text.split("start=")[1].strip()
    
    if ref_code:
        await state.update_data(ref_code=ref_code)
    
    await message.answer(
        '🦷 <b>Добро пожаловать в стоматологию "Тут Ваше имя"!</b>\n\n'
        'Давайте заполним анкету. Это займёт всего минуту.\n\n'
        '<b>Введите ваше имя:</b>\n'
        '<i>(только буквы, минимум 2 символа)</i>',
        parse_mode="HTML"
    )
    await state.set_state(RegistrationFSM.first_name)


@router.message(RegistrationFSM.first_name)
async def process_first_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    if not name:
        await message.answer(
            '❌ <b>Имя не может быть пустым!</b>\n\n'
            'Введите имя (только буквы, минимум 2 символа):',
            parse_mode="HTML"
        )
        return
    
    if len(name) < 2:
        await message.answer(
            '❌ <b>Имя слишком короткое!</b>\nМинимум 2 символа.\n\nВведите имя:',
            parse_mode="HTML"
        )
        return
    
    if len(name) > 50:
        await message.answer(
            '❌ <b>Имя слишком длинное!</b>\nМаксимум 50 символов.\n\nВведите имя:',
            parse_mode="HTML"
        )
        return
    
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\-]+$', name):
        await message.answer(
            '❌ <b>Некорректное имя!</b>\n\n'
            'Имя должно содержать <b>только буквы</b> (русские или английские).\n'
            'Цифры, пробелы и спецсимволы запрещены.\n\n'
            '<i>Пример: Иван, Анна-Мария, John</i>\n\nВведите имя:',
            parse_mode="HTML"
        )
        return
    
    await state.update_data(first_name=name.title())
    await message.answer(
        f'✅ Имя: <b>{name.title()}</b>\n\n'
        f'<b>Введите вашу фамилию:</b>\n'
        f'<i>(только буквы, минимум 2 символа)</i>',
        parse_mode="HTML"
    )
    await state.set_state(RegistrationFSM.last_name)


@router.message(RegistrationFSM.last_name)
async def process_last_name(message: Message, state: FSMContext):
    surname = message.text.strip()
    
    if not surname:
        await message.answer(
            '❌ <b>Фамилия не может быть пустой!</b>\n\nВведите фамилию:',
            parse_mode="HTML"
        )
        return
    
    if len(surname) < 2:
        await message.answer(
            '❌ <b>Фамилия слишком короткая!</b>\nМинимум 2 символа.\n\nВведите фамилию:',
            parse_mode="HTML"
        )
        return
    
    if len(surname) > 50:
        await message.answer(
            '❌ <b>Фамилия слишком длинная!</b>\nМаксимум 50 символов.\n\nВведите фамилию:',
            parse_mode="HTML"
        )
        return
    
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\-]+$', surname):
        await message.answer(
            '❌ <b>Некорректная фамилия!</b>\n\n'
            'Фамилия должна содержать <b>только буквы</b>.\n'
            'Цифры и спецсимволы запрещены.\n\nВведите фамилию:',
            parse_mode="HTML"
        )
        return
    
    await state.update_data(last_name=surname.title())
    await message.answer(
        f'✅ Фамилия: <b>{surname.title()}</b>\n\n'
        f'<b>Теперь отправьте ваш номер телефона:</b>\n'
        f'<i>Пример: +87771234567</i>\n\n'
        f'⚠️ Один номер — один аккаунт.',
        parse_mode="HTML"
    )
    await state.set_state(RegistrationFSM.phone)


@router.message(RegistrationFSM.phone)
async def process_phone_manual(message: Message, state: FSMContext):
    phone_raw = message.text.strip()
    
    if not validate_phone(phone_raw):
        await message.answer(
            '❌ <b>Некорректный номер телефона!</b>\n\n'
            'Введите номер в формате:\n'
            '<i>+7771234567</i> или <i>87771234567</i>\n'
            'Допустимы только цифры и знак +',
            parse_mode="HTML"
        )
        return
    
    phone = format_phone(phone_raw)
    
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) < 10:
        await message.answer(
            '❌ <b>Номер слишком короткий!</b>\n\n'
            'Введите полный номер (10-11 цифр).\n'
            '<i>Пример: +79161234567</i>',
            parse_mode="HTML"
        )
        return
    
    if len(digits_only) > 12:
        await message.answer(
            '❌ <b>Номер слишком длинный!</b>\n\n'
            'Введите корректный номер.\n'
            '<i>Пример: +77771234567</i>',
            parse_mode="HTML"
        )
        return
    
    if await phone_exists(phone):
        await message.answer(
            '❌ <b>Этот номер телефона уже зарегистрирован!</b>\n\n'
            '⚠️ Один номер телефона может быть привязан <b>только к одному аккаунту</b>.\n\n'
            'Если это ваш номер и вы забыли данные:\n'
            '• Обратитесь к администратору\n'
            '• Или используйте другой номер\n\n'
            'Введите другой номер телефона:',
            parse_mode="HTML"
        )
        return
    
    await state.update_data(phone=phone)
    data = await state.get_data()
    
    await message.answer(
        '📋 <b>Проверьте данные:</b>\n\n'
        f'👤 Имя: <b>{data["first_name"]}</b>\n'
        f'👤 Фамилия: <b>{data["last_name"]}</b>\n'
        f'📱 Телефон: <b>{phone}</b>\n\n'
        f'Всё верно? Отлично!\n\n'
        f'Последний шаг — <b>подписка на наш Instagram</b> 📸\n'
        f'Там мы публикуем акции, результаты работ и полезные советы!',
        parse_mode="HTML",
        reply_markup=get_instagram_link_keyboard()
    )
    await state.set_state(RegistrationFSM.instagram)


@router.callback_query(RegistrationFSM.instagram, F.data == "insta_check")
async def process_instagram_check(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('✅ <b>Спасибо за подписку!</b>\n\nЗавершаем регистрацию...', parse_mode="HTML")
    await complete_registration(callback.message, state, callback.from_user.id, instagram_subscribed=True)


@router.callback_query(RegistrationFSM.instagram, F.data == "insta_skip")
async def process_instagram_skip(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('⏭️ Подписка пропущена.\n\nЗавершаем регистрацию...', parse_mode="HTML")
    await complete_registration(callback.message, state, callback.from_user.id, instagram_subscribed=False)


async def complete_registration(message: Message, state: FSMContext, telegram_id: int, instagram_subscribed: bool = False):
    data = await state.get_data()
    ref_code = generate_ref_code(telegram_id)
    invited_by = None
    
    if "ref_code" in data:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.ref_code == data["ref_code"])
            )
            referrer = result.scalar_one_or_none()
            if referrer and referrer.telegram_id != telegram_id:
                invited_by = referrer.id
    
    try:
        async with async_session() as session:
            new_user = User(
                telegram_id=telegram_id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                ref_code=ref_code,
                invited_by=invited_by,
                instagram_subscribed=instagram_subscribed,
            )
            session.add(new_user)
            await session.flush()

            if invited_by:
                referral = Referral(
                    referrer_id=invited_by,
                    referred_id=new_user.id,
                )
                session.add(referral)

            await session.commit()
            logger.info(f"Новый пользователь: {data['first_name']} {data['last_name']} (ID: {telegram_id})")
        
        welcome_text = (
            f'🎉 <b>Регистрация завершена!</b>\n\n'
            f'👤 {data["first_name"]} {data["last_name"]}\n'
            f'📱 {data["phone"]}\n\n'
            f'🎁 <b>Приветственный бонус:</b> 1 бесплатное вращение колеса фортуны!\n'
            f'Используйте его в разделе 🎰 Колесо фортуны\n\n'
            f'👥 Ваш реферальный код: <code>{ref_code}</code>\n'
            f'Приглашайте друзей и получайте скидки!'
        )
        
        if invited_by:
            welcome_text += '\n\n✅ Вас пригласил пользователь. Вы получите бонус после первого визита!'
        
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(is_admin=await is_admin(telegram_id))
        )
        
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        await message.answer(
            '❌ <b>Ошибка регистрации!</b>\n\n'
            'Пожалуйста, попробуйте позже или обратитесь к администратору.\n'
            'Для повторной регистрации используйте команду /start',
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    
    await state.clear()
