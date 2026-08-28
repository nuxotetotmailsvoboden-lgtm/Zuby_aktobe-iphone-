from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_bonus"),
        InlineKeyboardButton("🎡 Колесо фортуны", callback_data="wheel"),
        InlineKeyboardButton("🎟 Розыгрыш", callback_data="lottery_info"),
        InlineKeyboardButton("🔗 Рефералы", callback_data="ref_info"),
        InlineKeyboardButton("📋 Миссии", callback_data="missions"),
        InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"),
        InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        InlineKeyboardButton("🎥 Отзыв за бонус", callback_data="review_start"),
        InlineKeyboardButton("🏢 Выбрать бизнес", callback_data="choose_business")
    )
    return kb

def back_to_profile_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в профиль"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
    return kb
