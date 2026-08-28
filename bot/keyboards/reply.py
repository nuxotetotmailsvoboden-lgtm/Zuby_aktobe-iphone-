from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def phone_request_kb() -> ReplyKeyboardMarkup:
    """Клавиатура с запросом номера телефона"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("📱 Отправить номер телефона", request_contact=True))
    return kb
