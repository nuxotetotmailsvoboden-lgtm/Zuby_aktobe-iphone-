from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_referral_keyboard(ref_link: str) -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Копировать ссылку", callback_data=f"copy_ref_{ref_link}"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="ref_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu_main"),
    )
    
    return builder.as_markup()
