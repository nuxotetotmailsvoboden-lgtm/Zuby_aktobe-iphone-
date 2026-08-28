from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import logging
from datetime import datetime

from config import settings
from db.base import async_session
from db.models import User, Booking, ContentTask, Reward, Raffle, LogAction
from sqlalchemy import select, func
from keyboards.admin import (
    get_admin_main_keyboard,
    get_admin_content_keyboard,
    get_admin_users_keyboard,
    get_admin_bookings_keyboard,
    get_back_to_admin_keyboard,
)
from keyboards.main_menu import get_main_menu_keyboard
from services.discount import DiscountEngine
from services.booking_service import BookingService
from services.antifraud import AntiFraudService

logger = logging.getLogger(__name__)
router = Router(name='admin')


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.SUPERADMINS or telegram_id in settings.ADMINS


def is_superadmin(telegram_id: int) -> bool:
    return telegram_id in settings.SUPERADMINS


@router.callback_query(F.data == 'menu_admin')
async def show_admin_panel(callback: CallbackQuery):
    await callback.answer()
    if not is_admin(callback.from_user.id):
        await callback.answer('Доступ запрещён', show_alert=True)
        return

    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        bookings_today = await session.scalar(
            select(func.count(Booking.id)).where(
                Booking.status == 'confirmed',
                func.date(Booking.created_at) == func.current_date()
            )
        )
        pending_content = await session.scalar(
            select(func.count(ContentTask.id)).where(ContentTask.status == 'pending')
        )

    await callback.message.edit_text(
        f'⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n'
        f'👥 Пользователей: <b>{users_count}</b>\n'
        f'📅 Записей сегодня: <b>{bookings_today}</b>\n'
        f'📸 Контент на модерации: <b>{pending_content}</b>\n\n'
        f'Выберите раздел:',
        parse_mode='HTML',
        reply_markup=get_admin_main_keyboard(is_superadmin(callback.from_user.id))
    )


# ✅ НОВЫЙ ОБРАБОТЧИК — ГЕНЕРАЦИЯ РАСПИСАНИЯ
@router.callback_query(F.data == 'admin_generate_schedule')
async def generate_schedule_now(callback: CallbackQuery):
    await callback.answer()
    await BookingService.generate_week_schedule()
    await callback.answer('✅ Расписание сгенерировано на 14 дней!', show_alert=True)


@router.callback_query(F.data == 'admin_content')
async def show_content_moderation(callback: CallbackQuery):
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        result = await session.execute(
            select(ContentTask)
            .where(ContentTask.status == 'pending')
            .order_by(ContentTask.created_at.asc())
            .limit(10)
        )
        tasks = result.scalars().all()

    if not tasks:
        await callback.message.edit_text(
            '📸 <b>МОДЕРАЦИЯ КОНТЕНТА</b>\n\n<i>Нет контента на проверку</i>',
            parse_mode='HTML',
            reply_markup=get_back_to_admin_keyboard()
        )
        return

    task = tasks[0]
    async with async_session() as session:
        user_result = await session.execute(select(User).where(User.id == task.user_id))
        user = user_result.scalar_one_or_none()

    await callback.message.edit_text(
        f'📸 <b>КОНТЕНТ НА МОДЕРАЦИИ</b>\n\n'
        f'👤 Автор: {user.first_name} {user.last_name if user else "Неизвестно"}\n'
        f'📱 ID: {task.user_id}\n'
        f'📸 Тип: {task.content_type}\n'
        f'🔗 Ссылка: {task.link}\n'
        f'⏰ Создано: {task.created_at.strftime("%d.%m.%Y %H:%M")}\n\n'
        f'Осталось на проверке: <b>{len(tasks)}</b>',
        parse_mode='HTML',
        reply_markup=get_admin_content_keyboard(task.id)
    )


@router.callback_query(F.data.startswith('admin_approve_'))
async def approve_content(callback: CallbackQuery):
    await callback.answer()
    task_id = int(callback.data.replace('admin_approve_', ''))

    async with async_session() as session:
        result = await session.execute(select(ContentTask).where(ContentTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            await callback.answer('Задача не найдена', show_alert=True)
            return
        task.status = 'approved'
        task.reviewed_at = datetime.utcnow()
        bonus_map = {'post': 2.0, 'video': 4.0, 'viral': 7.0}
        bonus = bonus_map.get(task.content_type, 2.0)
        task.bonus = bonus
        await session.commit()

        await DiscountEngine.add_discount(user_id=task.user_id, amount=bonus, source='content')
        await AntiFraudService.update_score(task.user_id, 'content_approved')

    try:
        await callback.bot.send_message(
            task.user_id,
            f'✅ <b>КОНТЕНТ ОДОБРЕН!</b>\n\n📸 Тип: {task.content_type}\n🎁 Начислено: +{bonus}%\n\nСпасибо за активность!',
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f'Не удалось уведомить: {e}')

    await show_content_moderation(callback)


@router.callback_query(F.data.startswith('admin_reject_'))
async def reject_content(callback: CallbackQuery):
    await callback.answer()
    task_id = int(callback.data.replace('admin_reject_', ''))

    async with async_session() as session:
        result = await session.execute(select(ContentTask).where(ContentTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            await callback.answer('Задача не найдена', show_alert=True)
            return
        task.status = 'rejected'
        task.reviewed_at = datetime.utcnow()
        await session.commit()

    try:
        await callback.bot.send_message(
            task.user_id,
            '❌ <b>Контент отклонён</b>\n\nК сожалению, ваш контент не прошёл модерацию.\nВы можете попробовать снова!',
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f'Не удалось уведомить: {e}')

    await show_content_moderation(callback)


@router.callback_query(F.data == 'admin_bookings')
async def show_bookings_management(callback: CallbackQuery):
    await callback.answer()
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .where(Booking.status.in_(['confirmed', 'pending']))
            .order_by(Booking.date.asc(), Booking.time.asc())
            .limit(20)
        )
        bookings = result.scalars().all()

    if not bookings:
        await callback.message.edit_text(
            '📅 <b>УПРАВЛЕНИЕ ЗАПИСЯМИ</b>\n\n<i>Нет активных записей</i>',
            parse_mode='HTML',
            reply_markup=get_back_to_admin_keyboard()
        )
        return

    text = '📅 <b>ЗАПИСИ НА ПРИЁМ</b>\n\n'
    for b in bookings:
        text += f'#{b.id} | {b.date.strftime("%d.%m")} {b.time.strftime("%H:%M")}\n🦷 {b.service} | 👤 ID:{b.user_id}\n\n'

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_admin_bookings_keyboard(bookings))


@router.callback_query(F.data.startswith('admin_confirm_visit_'))
async def confirm_visit(callback: CallbackQuery):
    await callback.answer()
    booking_id = int(callback.data.replace('admin_confirm_visit_', ''))
    await BookingService.confirm_visit(booking_id, callback.from_user.id)
    await callback.answer('Визит подтверждён! Начислен кэшбек.', show_alert=True)
    await show_bookings_management(callback)


@router.callback_query(F.data == 'admin_users')
async def show_users_management(callback: CallbackQuery):
    await callback.answer()
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()).limit(20))
        users = result.scalars().all()
        total_users = await session.scalar(select(func.count(User.id)))

    text = f'👥 <b>ПОЛЬЗОВАТЕЛИ</b> (всего: {total_users})\n\n'
    for u in users:
        fraud_emoji = '🟢' if u.fraud_score >= 80 else '🟡' if u.fraud_score >= 50 else '🔴'
        shadow = ' 👻' if u.shadow_ban else ''
        text += f'{fraud_emoji} {u.first_name} {u.last_name}{shadow}\n   📱 {u.phone} | Визитов: {u.total_visits}\n   🎯 Score: {u.fraud_score} | VIP: {"⭐" if u.is_vip else "—"}\n\n'

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_admin_users_keyboard())


@router.callback_query(F.data == 'admin_fraud')
async def show_fraud_info(callback: CallbackQuery):
    await callback.answer()
    async with async_session() as session:
        banned = await session.scalar(select(func.count(User.id)).where(User.shadow_ban == True))
        low_score = await session.scalar(select(func.count(User.id)).where(User.fraud_score < 50))
        suspicious = await session.scalar(select(func.count(User.id)).where(User.fraud_score.between(50, 79)))

    await callback.message.edit_text(
        f'🕵️ <b>АНТИФРОД СТАТИСТИКА</b>\n\n'
        f'👻 Теневой бан: <b>{banned}</b>\n'
        f'🔴 Низкий score (<50): <b>{low_score}</b>\n'
        f'🟡 Подозрительные (50-79): <b>{suspicious}</b>',
        parse_mode='HTML',
        reply_markup=get_back_to_admin_keyboard()
    )
