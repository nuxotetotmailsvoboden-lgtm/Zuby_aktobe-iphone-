import re

def validate_full_name(name: str) -> bool:
    """Проверяет, что имя содержит только буквы, пробел, дефис (2-50 символов)"""
    pattern = r"^[A-Za-zА-Яа-яёЁ\s\-]{2,50}$"
    return bool(re.match(pattern, name.strip()))

def validate_phone(phone: str) -> bool:
    """Проверяет формат +7XXXXXXXXXX (ровно 12 символов)"""
    pattern = r"^\+7\d{10}$"
    return bool(re.match(pattern, phone.strip()))
