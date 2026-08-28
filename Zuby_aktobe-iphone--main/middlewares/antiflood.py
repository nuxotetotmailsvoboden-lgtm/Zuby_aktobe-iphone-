from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis
from config import settings
import logging

logger = logging.getLogger(__name__)


class AntiFloodMiddleware(BaseMiddleware):
    """
    Middleware для защиты от флуда
    
    Ограничения:
    - Сообщения: 10 в секунду
    - Callback: 5 в секунду
    """
    
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.message_limit = 10
        self.callback_limit = 5
        self.window = 1  # секунда
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        
        if isinstance(event, Message):
            limit = self.message_limit
            key = f"flood:msg:{user_id}"
        elif isinstance(event, CallbackQuery):
            limit = self.callback_limit
            key = f"flood:cb:{user_id}"
        else:
            return await handler(event, data)
        
        # Проверка лимита
        current = await self.redis.get(key)
        
        if current and int(current) >= limit:
            logger.warning(f"Флуд от user_id={user_id}")
            
            if isinstance(event, CallbackQuery):
                await event.answer("Слишком быстро! Подождите секунду.", show_alert=True)
            
            # Обновляем антифрод
            from services.antifraud import AntiFraudService
            await AntiFraudService.update_score(user_id, "activity")
            
            return
        
        # Увеличиваем счётчик
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window)
        await pipe.execute()
        
        return await handler(event, data)
