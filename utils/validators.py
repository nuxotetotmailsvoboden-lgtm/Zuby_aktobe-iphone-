import re
from datetime import datetime, timedelta
from typing import Optional


def validate_phone(phone: str) -> bool:
    """
    Проверка формата телефона
    Принимает: +79161234567, 89161234567, 9161234567
    """
    # Очищаем от пробелов, скобок, тире
    phone_clean = re.sub(r'[\s\(\)\-]', '', phone)
    
    # Проверяем российские номера
    pattern = r'^(\+7|8)?\d{10}$'
    return bool(re.match(pattern, phone_clean))


def format_phone(phone: str) -> str:
    """Приведение телефона к единому формату"""
    phone_clean = re.sub(r'[\s\(\)\-]', '', phone)
    if phone_clean.startswith('8'):
        phone_clean = '+7' + phone_clean[1:]
    elif phone_clean.startswith('7'):
        phone_clean = '+' + phone_clean
    elif len(phone_clean) == 10:
        phone_clean = '+7' + phone_clean
    return phone_clean


def validate_name(name: str) -> bool:
    """Проверка имени/фамилии (только буквы, минимум 2 символа)"""
    return bool(re.match(r'^[а-яА-ЯёЁa-zA-Z\-]{2,50}$', name.strip()))


def add_minutes(t: datetime.time, minutes: int) -> datetime.time:
    """Добавить минуты к времени"""
    dt = datetime.combine(datetime.today(), t)
    dt = dt + timedelta(minutes=minutes)
    return dt.time()


def generate_ref_code(telegram_id: int) -> str:
    """Генерация уникального реферального кода"""
    import hashlib
    hash_str = hashlib.md5(str(telegram_id).encode()).hexdigest()[:8].upper()
    return f"REF{hash_str}"
