from functools import wraps
from datetime import datetime, timedelta
from aiogram import types

# Простое хранилище времени последнего использования (в памяти)
_daily_limits = {}

def daily_limit(key_prefix: str, hours: int = 24):
    """Декоратор для ограничения частоты вызова callback-хендлера"""
    def decorator(func):
        @wraps(func)
        async def wrapper(call: types.CallbackQuery, *args, **kwargs):
            user_id = call.from_user.id
            key = f"{key_prefix}_{user_id}"
            now = datetime.now()
            if key in _daily_limits:
                last_time = _daily_limits[key]
                if now - last_time < timedelta(hours=hours):
                    await call.answer(f"Можно использовать раз в {hours} ч.", show_alert=True)
                    return
            _daily_limits[key] = now
            return await func(call, *args, **kwargs)
        return wrapper
    return decorator
