from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_content_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа контента"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📝 Пост (+2%)", callback_data="content_post"),
        InlineKeyboardButton(text="🎥 Видео (+3-5%)", callback_data="content_video"),
    )
    builder.row(
        InlineKeyboardButton(text="🌟 Вирусное (+до10%)", callback_data="content_viral"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu_main"),
    )
    
    return builder.as_markup()


def get_content_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отправки контента"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить на проверку", callback_data="content_confirm_send"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu_content"),
    )
    return builder.as_markup()
