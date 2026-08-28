from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_keyboard(is_super: bool = False) -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Записи", callback_data="admin_bookings"),
        InlineKeyboardButton(text="📸 Контент", callback_data="admin_content"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="🕵️ Антифрод", callback_data="admin_fraud"),
    )

    if is_super:
        builder.row(
            InlineKeyboardButton(text="📅 Сгенерировать расписание", callback_data="admin_generate_schedule"),
        )
        builder.row(
            InlineKeyboardButton(text="📩 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🎁 Скидки", callback_data="admin_discounts"),
        )
        builder.row(
            InlineKeyboardButton(text="🎉 Розыгрыш", callback_data="raffle_draw_test"),
            InlineKeyboardButton(text="📊 CSV выгрузка", callback_data="admin_export"),
        )

    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main"),
    )

    return builder.as_markup()


def get_admin_content_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации контента"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_{task_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{task_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⏭️ Пропустить", callback_data="admin_content"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В админ-панель", callback_data="menu_admin"),
    )

    return builder.as_markup()


def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В админ-панель", callback_data="menu_admin"),
    )

    return builder.as_markup()


def get_admin_bookings_keyboard(bookings: list) -> InlineKeyboardMarkup:
    """Клавиатура управления записями"""
    builder = InlineKeyboardBuilder()

    for b in bookings[:6]:
        builder.row(
            InlineKeyboardButton(
                text=f"✅ Визит: #{b.id} {b.date.strftime('%d.%m')}",
                callback_data=f"admin_confirm_visit_{b.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_bookings"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В админ-панель", callback_data="menu_admin"),
    )

    return builder.as_markup()


def get_receipt_approve_keyboard(user_id: int, receipt_id: str, amount: float) -> InlineKeyboardMarkup:
    """Клавиатура для модерации чеков администратором"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"receipt_approve_{user_id}_{receipt_id}_{amount}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"receipt_reject_{user_id}_{receipt_id}"
        ),
    )
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в админку"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="menu_admin"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main"))
    return builder.as_markup()
