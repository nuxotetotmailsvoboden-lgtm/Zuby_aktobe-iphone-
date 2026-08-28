from datetime import date, time, datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional, Tuple


SERVICES = [
    ("🦷 Консультация (30 мин)", "service_consult"),
    ("🦷 Чистка зубов (45 мин)", "service_cleaning"),
    ("🦷 Лечение кариеса (60 мин)", "service_caries"),
    ("🦷 Имплантация (90 мин)", "service_implant"),
    ("🦷 Отбеливание (60 мин)", "service_whitening"),
    ("🦷 Брекеты (60 мин)", "service_braces"),
]

SERVICE_DURATIONS = {
    "service_consult": 30,
    "service_cleaning": 45,
    "service_caries": 60,
    "service_implant": 90,
    "service_whitening": 60,
    "service_braces": 60,
}

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_booking_services_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name, callback in SERVICES:
        builder.row(InlineKeyboardButton(text=name, callback_data=callback))
    builder.row(InlineKeyboardButton(text="📋 Мои записи", callback_data="booking_my"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu_main"))
    return builder.as_markup()


def get_date_keyboard(available_dates: List[date], service_duration: int, show_more: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    limit = 12 if show_more else 6
    dates_to_show = available_dates[:limit]

    for i in range(0, len(dates_to_show), 3):
        row = []
        for j in range(3):
            if i + j < len(dates_to_show):
                d = dates_to_show[i + j]
                weekday = WEEKDAYS[d.weekday()]
                date_str = d.strftime("%d.%m")
                row.append(InlineKeyboardButton(
                    text=f"{weekday} {date_str}",
                    callback_data=f"date_{d.strftime('%Y-%m-%d')}"
                ))
        if row:
            builder.row(*row)

    nav_row = []
    if not show_more:
        nav_row.append(InlineKeyboardButton(text="📅 Все даты →", callback_data="booking_more_dates"))
    nav_row.append(InlineKeyboardButton(text="◀️ Назад к услугам", callback_data="menu_booking"))
    builder.row(*nav_row)
    return builder.as_markup()


def get_time_keyboard(available_slots: List[time], selected_date: date) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not available_slots:
        builder.row(InlineKeyboardButton(text="❌ Нет свободных слотов", callback_data="no_slots"))
    else:
        # Показываем все слоты, 4 в ряд
        for i in range(0, len(available_slots), 4):
            row = []
            for j in range(4):
                if i + j < len(available_slots):
                    t = available_slots[i + j]
                    row.append(InlineKeyboardButton(
                        text=t.strftime("%H:%M"),
                        callback_data=f"time_{t.strftime('%H:%M')}"
                    ))
            if row:
                builder.row(*row)

    # Кнопка назад — возвращает к списку дат
    builder.row(InlineKeyboardButton(text="◀️ Выбрать другую дату", callback_data="booking_more_dates"))
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="booking_confirm"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Добавить комментарий", callback_data="booking_add_comment"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить", callback_data="booking_cancel"),
    )
    return builder.as_markup()


def get_booking_success_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Мои записи", callback_data="booking_my"))
    builder.row(InlineKeyboardButton(text="🎁 Мои скидки", callback_data="menu_discounts"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main"))
    return builder.as_markup()


def get_alternative_keyboard(alternative: Optional[Tuple[date, time]] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if alternative:
        alt_date, alt_time = alternative
        builder.row(InlineKeyboardButton(
            text=f"✅ Да, {alt_date.strftime('%d.%m')} в {alt_time.strftime('%H:%M')}",
            callback_data=f"alt_accept_{alt_date.strftime('%Y-%m-%d')}_{alt_time.strftime('%H-%M')}"
        ))
    builder.row(InlineKeyboardButton(text="🔄 Искать ещё", callback_data="alt_search_again"))
    builder.row(InlineKeyboardButton(text="↩️ Выбрать другую услугу", callback_data="menu_booking"))
    return builder.as_markup()
