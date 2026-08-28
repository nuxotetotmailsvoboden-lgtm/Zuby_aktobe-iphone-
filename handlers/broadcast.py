from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import logging

from config import settings
from db.base import async_session
from db.models import User
from sqlalchemy import select, func
from states.fsm import BroadcastFSM
from keyboards.admin import get_back_to_admin_keyboard

logger = logging.getLogger(__name__)
router = Router(name="broadcast")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.SUPERADMINS or telegram_id in settings.ADMINS


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    await callback.answer()
    
    if not is_admin(callback.from_user.id):
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📩 Всем", callback_data="broadcast_all"))
    builder.row(InlineKeyboardButton(text="👥 Активным (7 дн)", callback_data="broadcast_active"))
    builder.row(InlineKeyboardButton(text="😴 Неактивным (30+ дн)", callback_data="broadcast_inactive"))
    builder.row(InlineKeyboardButton(text="⭐ VIP", callback_data="broadcast_vip"))
    builder.row(InlineKeyboardButton(text="◀️ В админ-панель", callback_data="menu_admin"))
    
    await callback.message.edit_text(
        "📩 <b>РАССЫЛКА</b>\n\n"
        "Выберите сегмент получателей:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BroadcastFSM.segment)


@router.callback_query(BroadcastFSM.segment, F.data.startswith("broadcast_"))
async def select_segment(callback: CallbackQuery, state: FSMContext):
    """Выбор сегмента"""
    await callback.answer()
    
    segment = callback.data.replace("broadcast_", "")
    
    segment_names = {
        "all": "Всем пользователям",
        "active": "Активным (за 7 дней)",
        "inactive": "Неактивным (30+ дней)",
        "vip": "VIP пользователям",
    }
    
    segment_name = segment_names.get(segment, segment)
    
    await state.update_data(broadcast_segment=segment)
    
    await callback.message.edit_text(
        f"📩 <b>РАССЫЛКА</b>\n"
        f"👥 Сегмент: {segment_name}\n\n"
        f"<b>Отправьте сообщение для рассылки:</b>\n\n"
        f"<i>Поддерживается HTML и эмодзи</i>\n"
        f"<i>Для отмены нажмите /cancel</i>",
        parse_mode="HTML",
    )
    await state.set_state(BroadcastFSM.message)


@router.message(BroadcastFSM.message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    data = await state.get_data()
    segment = data.get("broadcast_segment", "all")
    
    # Сохраняем сообщение
    await state.update_data(
        broadcast_text=message.text,
        broadcast_entities=message.entities,
    )
    
    # Подсчитываем количество получателей
    from datetime import datetime, timedelta
    
    async with async_session() as session:
        query = select(func.count(User.id))
        
        now = datetime.utcnow()
        
        if segment == "active":
            query = query.where(User.last_activity >= now - timedelta(days=7))
        elif segment == "inactive":
            query = query.where(User.last_activity < now - timedelta(days=30))
        elif segment == "vip":
            query = query.where(User.is_vip == True)
        
        count = await session.scalar(query)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
    )
    
    await message.answer(
        f"📩 <b>ПРОВЕРКА РАССЫЛКИ</b>\n\n"
        f"👥 Получателей: <b>{count}</b>\n\n"
        f"📝 Сообщение:\n"
        f"{message.text[:200]}...\n\n"
        f"Подтвердите отправку:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BroadcastFSM.confirm)


@router.callback_query(BroadcastFSM.confirm, F.data == "broadcast_send")
async def send_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отправить рассылку"""
    await callback.answer()
    
    data = await state.get_data()
    segment = data.get("broadcast_segment", "all")
    text = data.get("broadcast_text", "")
    
    from datetime import datetime, timedelta
    
    async with async_session() as session:
        query = select(User.telegram_id)
        
        now = datetime.utcnow()
        
        if segment == "active":
            query = query.where(User.last_activity >= now - timedelta(days=7))
        elif segment == "inactive":
            query = query.where(User.last_activity < now - timedelta(days=30))
        elif segment == "vip":
            query = query.where(User.is_vip == True)
        
        result = await session.execute(query)
        users = result.scalars().all()
    
    success = 0
    failed = 0
    
    progress_msg = await callback.message.edit_text(
        f"📩 <b>РАССЫЛКА НАЧАТА</b>\n\n"
        f"👥 Всего: {len(users)}\n"
        f"✅ Отправлено: 0\n"
        f"❌ Ошибок: 0",
        parse_mode="HTML"
    )
    
    for i, user_id in enumerate(users):
        try:
            await callback.bot.send_message(user_id, text, parse_mode="HTML")
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка отправки user_id={user_id}: {e}")
        
        # Обновляем прогресс каждые 10 сообщений
        if (i + 1) % 10 == 0:
            try:
                await progress_msg.edit_text(
                    f"📩 <b>РАССЫЛКА ИДЁТ</b>\n\n"
                    f"👥 Всего: {len(users)}\n"
                    f"✅ Отправлено: {success}\n"
                    f"❌ Ошибок: {failed}\n"
                    f"📊 Прогресс: {((i+1)/len(users)*100):.0f}%",
                    parse_mode="HTML"
                )
            except:
                pass
        
        # Небольшая задержка чтобы не упереться в лимиты Telegram
        if (i + 1) % 30 == 0:
            import asyncio
            await asyncio.sleep(1)
    
    await progress_msg.edit_text(
        f"📩 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
        f"👥 Всего: {len(users)}\n"
        f"✅ Отправлено: {success}\n"
        f"❌ Ошибок: {failed}",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отменить рассылку"""
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Рассылка отменена",
        reply_markup=get_back_to_admin_keyboard()
    )
