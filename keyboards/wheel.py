from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_wheel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура колеса фортуны"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 КРУТИТЬ КОЛЕСО!", callback_data="wheel_spin"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 История вращений", callback_data="wheel_history"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu_main"),
    )
    
    return builder.as_markup()


def get_wheel_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после вращения"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Крутить ещё (завтра)", callback_data="wheel_cooldown"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Мои скидки", callback_data="menu_discounts"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu_main"),
    )
    
    return builder.as_markup()
