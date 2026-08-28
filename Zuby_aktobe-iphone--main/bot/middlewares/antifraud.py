from datetime import datetime, timedelta

# Простая проверка по Telegram ID (в памяти)
registration_attempts = {}

async def check_registration_limit(user_id: int) -> bool:
    """Не более 3 попыток регистрации в час с одного ID"""
    now = datetime.now()
    key = f"reg_{user_id}"
    if key in registration_attempts:
        attempts, first_time = registration_attempts[key]
        if now - first_time < timedelta(hours=1) and attempts >= 3:
            return False
        registration_attempts[key] = (attempts + 1, first_time)
    else:
        registration_attempts[key] = (1, now)
    return True
