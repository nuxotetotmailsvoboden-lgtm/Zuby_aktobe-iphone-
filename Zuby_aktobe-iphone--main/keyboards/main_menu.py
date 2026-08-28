from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎰 Колесо фортуны", callback_data="menu_wheel"),
        InlineKeyboardButton(text="📅 Запись на приём", callback_data="menu_booking"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Мои скидки", callback_data="menu_discounts"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="menu_referral"),
    )
    builder.row(
        InlineKeyboardButton(text="📸 Отправить контент", callback_data="menu_content"),
        InlineKeyboardButton(text="🎉 Розыгрыш призов", callback_data="menu_raffle"),
    )
    builder.row(
        InlineKeyboardButton(text="🧾 Чек — кэшбек", callback_data="cashback_send_receipt"),  # ← ВОТ ЗДЕСЬ
    )
    builder.row(
        InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts"),
        InlineKeyboardButton(text="ℹ️ О клинике", callback_data="menu_about"),
    )
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="menu_admin"),
        )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "menu_main") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data),
    )
    return builder.as_markup()
