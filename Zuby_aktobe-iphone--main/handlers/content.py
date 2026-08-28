from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import logging

from states.fsm import ContentFSM
from keyboards.content import get_content_type_keyboard, get_content_confirm_keyboard
from keyboards.main_menu import get_back_keyboard, get_main_menu_keyboard
from db.base import async_session
from db.models import ContentTask
from services.discount import DiscountEngine
from services.antifraud import AntiFraudService

logger = logging.getLogger(__name__)
router = Router(name="content")

CONTENT_BONUSES = {
    "post": (2.0, "Пост"),
    "video": (4.0, "Видео"),
    "viral": (7.0, "Вирусное"),
}


@router.callback_query(F.data.startswith("content_"))
async def process_content_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа контента"""
    await callback.answer()
    
    content_type = callback.data.replace("content_", "")
    
    if content_type not in CONTENT_BONUSES:
        return
    
    bonus, type_name = CONTENT_BONUSES[content_type]
    
    await state.update_data(
        content_type=content_type,
        content_bonus=bonus,
        content_type_name=type_name,
    )
    
    await callback.message.edit_text(
        f'📸 <b>{type_name}</b>\n\n'
        f'🎁 Награда: <b>до +{bonus}%</b>\n\n'
        f'📋 <b>Отправьте ссылку на ваш пост/видео:</b>\n\n'
        f'<i>Это может быть:</i>\n'
        f'• Пост в Instagram\n'
        f'• Видео в TikTok\n'
        f'• Отзыв на 2GIS/Yandex\n'
        f'• Пост ВКонтакте\n\n'
        f'<b>Важно:</b> контент должен быть о нашей клинике!',
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_content")
    )
    await state.set_state(ContentFSM.link)


@router.message(ContentFSM.link)
async def process_content_link(message: Message, state: FSMContext):
    """Обработка ссылки на контент"""
    link = message.text.strip()
    
    if not link.startswith(("http://", "https://", "www.")):
        await message.answer(
            '❌ <b>Некорректная ссылка!</b>\n\n'
            'Пожалуйста, отправьте полную ссылку (начинается с http:// или https://)\n\n'
            '<i>Пример: https://instagram.com/p/...</i>',
            parse_mode="HTML",
            reply_markup=get_back_keyboard("menu_content")
        )
        return
    
    if len(link) > 500:
        await message.answer(
            '❌ Ссылка слишком длинная (максимум 500 символов)',
            parse_mode="HTML",
            reply_markup=get_back_keyboard("menu_content")
        )
        return
    
    data = await state.get_data()
    content_type = data.get("content_type")
    content_type_name = data.get("content_type_name", "Контент")
    bonus = data.get("content_bonus", 2.0)
    
    async with async_session() as session:
        task = ContentTask(
            user_id=message.from_user.id,
            content_type=content_type,
            link=link,
            status="pending",
        )
        session.add(task)
        await session.commit()
    
    await message.answer(
        f'✅ <b>ЗАЯВКА ОТПРАВЛЕНА!</b>\n\n'
        f'📸 Тип: {content_type_name}\n'
        f'🔗 Ссылка: {link[:50]}...\n'
        f'🎁 Ожидаемая награда: +{bonus}%\n\n'
        f'⏳ <b>Статус:</b> на модерации\n'
        f'Мы проверим контент в течение 24 часов.\n'
        f'Вы получите уведомление о результате.',
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
    
    await notify_admins_new_content(message, task)
    await state.clear()


async def notify_admins_new_content(message: Message, task: ContentTask):
    """Уведомить админов о новом контенте"""
    from config import settings
    
    admin_text = (
        f'📸 <b>НОВЫЙ КОНТЕНТ НА МОДЕРАЦИЮ</b>\n\n'
        f'👤 Пользователь: {message.from_user.full_name}\n'
        f'📱 ID: {message.from_user.id}\n'
        f'📸 Тип: {task.content_type}\n'
        f'🔗 Ссылка: {task.link}\n'
        f'⏰ Создано: {task.created_at.strftime("%d.%m.%Y %H:%M")}\n\n'
        f'Используйте админ-панель для модерации.'
    )
    
    for admin_id in settings.SUPERADMINS + settings.ADMINS:
        try:
            await message.bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f'Не удалось уведомить админа {admin_id}: {e}')
