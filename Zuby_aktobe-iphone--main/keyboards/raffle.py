from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_raffle_keyboard(raffles: list) -> InlineKeyboardMarkup:
    """Клавиатура розыгрыша"""
    builder = InlineKeyboardBuilder()
    
    for raffle in raffles:
        builder.row(
            InlineKeyboardButton(
                text=f'🎟️ Участвовать: {raffle.prize_name}',
                callback_data=f'raffle_join_{raffle.id}'
            )
        )
    
    builder.row(
        InlineKeyboardButton(text='📊 Мои шансы', callback_data='raffle_chances'),
    )
    builder.row(
        InlineKeyboardButton(text='◀️ Назад в меню', callback_data='menu_main'),
    )
    
    return builder.as_markup()
