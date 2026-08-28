from typing import Any, Awaitable, Callable, Dict
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
import logging

from db.base import async_session
from db.models import User

logger = logging.getLogger(__name__)


class SaveActivityMiddleware(BaseMiddleware):
    """Middleware для сохранения активности пользователя"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.last_activity = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения активности: {e}")
        
        return await handler(event, data)
