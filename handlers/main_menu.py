from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from keyboards.main_menu import get_main_menu_keyboard, get_back_keyboard
from keyboards.wheel import get_wheel_keyboard
from keyboards.booking import get_booking_services_keyboard
from keyboards.referral import get_referral_keyboard
from keyboards.content import get_content_type_keyboard

logger = logging.getLogger(__name__)
router = Router(name="main_menu")


async def is_admin_check(telegram_id: int) -> bool:
    from config import settings
    return telegram_id in settings.SUPERADMINS or telegram_id in settings.ADMINS


@router.callback_query(F.data == "menu_main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        '🦷 <b>Главное меню</b>\n\nВыберите нужный раздел:',
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=await is_admin_check(callback.from_user.id))
    )


# ==================== КОЛЕСО ФОРТУНЫ ====================

@router.callback_query(F.data == "menu_wheel")
async def show_wheel_menu(callback: CallbackQuery):
    await callback.answer()
    from services.discount import DiscountEngine
    discount = await DiscountEngine.get_available_discount(callback.from_user.id)
    
    await callback.message.edit_text(
        '🎰 <b>КОЛЕСО ФОРТУНЫ</b>\n\n'
        'Испытайте удачу и получите скидку на лечение!\n\n'
        '🎲 <b>Призы:</b>\n'
        '• 0% — 55%\n'
        '• 1% — 20%\n'
        '• 2% — 10%\n'
        '• 3% — 7%\n'
        '• 5% — 4%\n'
        '• 10% — 2%\n'
        '• 20% — 0.8%\n'
        '• 30% — 0.15%\n'
        '• 50% — 0.04%\n'
        '• 100% — 0.01%\n\n'
        f'💎 Ваша текущая скидка: <b>{discount}%</b>\n\n'
        '🔄 Можно крутить 1 раз в 24 часа!',
        parse_mode="HTML",
        reply_markup=get_wheel_keyboard()
    )


# ==================== ЗАПИСЬ НА ПРИЁМ ====================

@router.callback_query(F.data == "menu_booking")
async def show_booking_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        '📅 <b>ЗАПИСЬ НА ПРИЁМ</b>\n\nВыберите услугу:',
        parse_mode="HTML",
        reply_markup=get_booking_services_keyboard()
    )


# ==================== МОИ СКИДКИ ====================

@router.callback_query(F.data == "menu_discounts")
async def show_discounts_menu(callback: CallbackQuery):
    await callback.answer()
    from services.discount import DiscountEngine
    from datetime import datetime
    
    discount = await DiscountEngine.get_available_discount(callback.from_user.id)
    all_discounts = await DiscountEngine.get_user_discounts(callback.from_user.id)
    
    now = datetime.utcnow()
    active_discounts = [d for d in all_discounts if d.expires_at > now and not d.is_expired and not d.is_frozen]
    frozen_discounts = [d for d in all_discounts if d.is_frozen and d.expires_at > now]
    
    text = (
        '🎁 <b>МОИ СКИДКИ</b>\n\n'
        f'💎 Доступно: <b>{discount}%</b>\n'
        '📊 Максимальная: <b>40%</b>\n\n'
    )
    
    if active_discounts:
        text += '<b>✅ Активные скидки:</b>\n'
        for d in active_discounts[:10]:
            days_left = (d.expires_at - now).days
            source_emoji = {"wheel": "🎰", "referral": "👥", "visit": "🦷", "content": "📸", "cashback": "💰"}.get(d.source, "🎁")
            text += f'{source_emoji} {d.source}: +{d.amount}% (сгорит через {days_left} дн.)\n'
    
    if frozen_discounts:
        text += '\n<b>🔒 Заморожено до визита:</b>\n'
        for d in frozen_discounts[:5]:
            text += f'• {d.source}: +{d.amount}%\n'
    
    if not active_discounts and not frozen_discounts:
        text += '\n<i>У вас пока нет активных скидок</i>\n<i>Крутите колесо или приглашайте друзей!</i>\n'
    
    text += f'\nВсего скидок: {len(all_discounts)}'
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_keyboard("menu_main"))


# ==================== РЕФЕРАЛЫ ====================

@router.callback_query(F.data == "menu_referral")
async def show_referral_menu(callback: CallbackQuery):
    await callback.answer()
    from db.base import async_session
    from db.models import User, Referral
    from sqlalchemy import select
    
    telegram_id = callback.from_user.id
    
    async with async_session() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text('❌ Пользователь не найден. Используйте /start', parse_mode="HTML")
            return
        
        refs_result = await session.execute(select(Referral).where(Referral.referrer_id == user.id))
        all_refs = refs_result.scalars().all()
        visited_refs = [r for r in all_refs if r.visited]
        rewarded_refs = [r for r in all_refs if r.reward_given]
        
        bot_me = await callback.bot.me()
        ref_link = f'https://t.me/{bot_me.username}?start={user.ref_code}'
    
    await callback.message.edit_text(
        f'👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n\n'
        f'🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n\n'
        f'📊 <b>Статистика:</b>\n'
        f'• Приглашено: <b>{len(all_refs)}</b>\n'
        f'• С визитами: <b>{len(visited_refs)}</b>\n'
        f'• Начислено: <b>{len(rewarded_refs)}%</b>\n\n'
        f'💰 <b>Правила:</b>\n'
        f'• +1% за каждого друга после визита\n'
        f'• Максимум: <b>15%</b>\n\n'
        f'📋 Скопируйте ссылку и отправьте друзьям!',
        parse_mode="HTML",
        reply_markup=get_referral_keyboard(ref_link)
    )


# ✅ ОБРАБОТЧИК «КОПИРОВАТЬ ССЫЛКУ»
@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_referral_link(callback: CallbackQuery):
    ref_link = callback.data.replace("copy_ref_", "")
    await callback.answer(f"Ссылка скопирована:\n{ref_link}", show_alert=True)


# ✅ ОБРАБОТЧИК «СТАТИСТИКА»
@router.callback_query(F.data == "ref_stats")
async def show_referral_stats(callback: CallbackQuery):
    await callback.answer()
    from db.base import async_session
    from db.models import User, Referral
    from sqlalchemy import select
    
    telegram_id = callback.from_user.id
    
    async with async_session() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        refs_result = await session.execute(select(Referral).where(Referral.referrer_id == user.id))
        refs = refs_result.scalars().all()
        
        if not refs:
            await callback.message.edit_text(
                "📊 <b>СТАТИСТИКА РЕФЕРАЛОВ</b>\n\n"
                "<i>У вас пока нет приглашённых пользователей.</i>\n\n"
                "Отправьте свою реферальную ссылку друзьям!",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("menu_referral")
            )
            return
        
        text = "📊 <b>СТАТИСТИКА РЕФЕРАЛОВ</b>\n\n"
        text += f"👥 Всего приглашено: <b>{len(refs)}</b>\n"
        text += f"✅ С визитами: <b>{len([r for r in refs if r.visited])}</b>\n"
        text += f"🎁 Начислено бонусов: <b>{len([r for r in refs if r.reward_given])}%</b>\n\n"
        text += "<b>Список приглашённых:</b>\n"
        
        for i, ref in enumerate(refs[:20], 1):
            ref_user_result = await session.execute(select(User).where(User.id == ref.referred_id))
            ref_user = ref_user_result.scalar_one_or_none()
            if ref_user:
                status = "✅" if ref.visited else "⏳"
                bonus = "🎁" if ref.reward_given else "—"
                text += f"{i}. {status} {ref_user.first_name} {ref_user.last_name} | Бонус: {bonus}\n"
        
        if len(refs) > 20:
            text += f"\n... и ещё {len(refs) - 20} человек"
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_back_keyboard("menu_referral")
        )


# ==================== КОНТЕНТ ====================

@router.callback_query(F.data == "menu_content")
async def show_content_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        '📸 <b>ОТПРАВКА КОНТЕНТА</b>\n\n'
        'Опубликуйте пост или видео о нашей клинике\nи получите дополнительную скидку!\n\n'
        '🎁 <b>Награды:</b>\n'
        '• Пост: <b>+2%</b>\n'
        '• Видео: <b>+3-5%</b>\n'
        '• Вирусное: <b>до +10%</b>\n\n'
        '📊 Максимум за контент: <b>10%</b>\n\n'
        'Выберите тип контента:',
        parse_mode="HTML",
        reply_markup=get_content_type_keyboard()
    )


# ==================== РОЗЫГРЫШ ====================

@router.callback_query(F.data == "menu_raffle")
async def show_raffle_menu(callback: CallbackQuery):
    await callback.answer()
    from db.base import async_session
    from db.models import Raffle, RaffleParticipant, User, Referral
    from sqlalchemy import select
    
    telegram_id = callback.from_user.id
    
    async with async_session() as session:
        raffles_result = await session.execute(select(Raffle).where(Raffle.status == "active"))
        raffles = raffles_result.scalars().all()
        
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        
        if user:
            refs_result = await session.execute(select(Referral).where(Referral.referrer_id == user.id))
            refs = refs_result.scalars().all()
            weight = (len(refs) * 1.5) + (user.total_visits * 3) + (user.total_checks / 1000)
        else:
            weight = 0
    
    text = (
        '🎉 <b>РОЗЫГРЫШ ПРИЗОВ</b>\n\n'
        f'📊 <b>Ваш вес:</b> {weight:.2f}\n'
        '<i>(растёт за рефералов и визиты)</i>\n\n'
    )
    
    if raffles:
        text += '<b>Активные розыгрыши:</b>\n'
        for r in raffles:
            text += f'🏆 {r.prize_name}\n'
    else:
        text += '<i>Сейчас нет активных розыгрышей</i>\n'
    
    text += '\nЧем больше вес — тем выше шанс победить!'
    
    from keyboards.raffle import get_raffle_keyboard
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_raffle_keyboard(raffles))


# ==================== КОНТАКТЫ ====================

@router.callback_query(F.data == "menu_contacts")
async def show_contacts(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        '📞 <b>КОНТАКТЫ</b>\n\n'
        '🦷 <b>Стоматология "ИМЯ"</b>\n\n'
        '📍 <b>Адрес:</b>\nг. АДРЕС (могу по 2гис проложить путь)\n\n'
        '📱 <b>Телефон:</b>\n+7‒700‒123‒45‒67\n\n'
        '🕐 <b>Часы работы:</b>\nПн-Пт: 09:00 - 22:00\nСб: 10:00 - 20:00\nВс: выходной\n\n'
        '📸 <b>Instagram:</b>\nТУТ ССЫЛКА НА ВАШ ИНСТe\n\n'
        '🌐 <b>Сайт:</b>\nТУТ ССЫЛКА,
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_main")
    )


# ==================== О КЛИНИКЕ ====================

@router.callback_query(F.data == "menu_about")
async def show_about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        'ℹ️ <b>О КЛИНИКЕ</b>\n\n'
        '🦷 <b>ВАЩА стомотология</b> — современная стоматология\nс опытом работы более N лет.\n\n'
        '✅ <b>Наши преимущества:</b>\n'
        '• Новейшее оборудование\n'
        '• Опытные врачи\n'
        '• Безболезненное лечение\n'
        '• Доступные цены\n'
        '• Стерильность и безопасность\n\n'
        '⭐ <b>Рейтинг:</b> 4.9/5\n'
        '👥 <b>Более N довольных пациентов</b>\n\n'
        'Запишитесь на бесплатную консультацию\nпрямо сейчас в разделе 📅 Запись на приём!',
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_main")
    )
