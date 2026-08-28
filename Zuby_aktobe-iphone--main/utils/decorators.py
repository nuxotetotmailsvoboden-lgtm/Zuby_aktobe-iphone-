import functools
import logging
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    @functools.wraps(func)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        from config import settings
        user_id = event.from_user.id
        
        if user_id not in settings.SUPERADMINS and user_id not in settings.ADMINS:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён", show_alert=True)
            else:
                await event.answer("⛔ У вас нет прав для этой команды")
            return
        
        return await func(event, *args, **kwargs)
    return wrapper


def superadmin_only(func: Callable) -> Callable:
    """Декоратор для проверки прав суперадмина"""
    @functools.wraps(func)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        from config import settings
        user_id = event.from_user.id
        
        if user_id not in settings.SUPERADMINS:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Только для суперадминов", show_alert=True)
            else:
                await event.answer("⛔ Только для суперадминов")
            return
        
        return await func(event, *args, **kwargs)
    return wrapper


def log_action(action_name: str):
    """Декоратор для логирования действий"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Action: {action_name} | Args: {args[:2]}...")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Action {action_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Action {action_name} failed: {e}")
                raise
        return wrapper
    return decorator


def rate_limit(seconds: int):
    """Декоратор для ограничения частоты вызовов (простой вариант)"""
    import time
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
            user_id = event.from_user.id
            now = time.time()
            
            if user_id in cache:
                last_call = cache[user_id]
                if now - last_call < seconds:
                    remaining = int(seconds - (now - last_call))
                    if isinstance(event, CallbackQuery):
                        await event.answer(f"⏳ Подождите {remaining} сек.", show_alert=True)
                    return
                else:
                    del cache[user_id]
            
            cache[user_id] = now
            return await func(event, *args, **kwargs)
        return wrapper
    return decorator


def catch_errors(func: Callable) -> Callable:
    """Декоратор для отлова и логирования ошибок"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Unhandled error in {func.__name__}: {e}")
            # Можно добавить уведомление админу
            return None
    return wrapper
