from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_instagram_check_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура проверки подписки на Instagram"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Я подписался", callback_data="insta_check"),
    )
    return builder.as_markup()


def get_instagram_link_keyboard() -> InlineKeyboardMarkup:
    """Ссылка на Instagram"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📸 Перейти в Instagram", url="ТУТ ВАШ АККАУНТe"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Я подписался", callback_data="insta_check"),
    )
    return builder.as_markup()
