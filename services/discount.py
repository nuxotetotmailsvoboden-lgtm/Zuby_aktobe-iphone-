from datetime import datetime, timedelta
from sqlalchemy import select, and_
import logging

from db.base import async_session
from db.models import Reward, User, Booking

logger = logging.getLogger(__name__)


class DiscountEngine:
    """Движок управления скидками"""
    
    MAX_TOTAL_DISCOUNT = 40.0
    MAX_DISCOUNT_WITHOUT_VISIT = 15.0
    MAX_REFERRAL_DISCOUNT = 15.0
    MAX_CONTENT_DISCOUNT = 10.0
    MAX_CASHBACK_DISCOUNT = 15.0
    DISCOUNT_LIFETIME_DAYS = 40
    
    @staticmethod
    async def add_discount(
        user_id: int,
        amount: float,
        source: str,
        lifetime_days: int = None,
        freeze_until: datetime = None,
    ) -> Reward | None:
        """
        Добавить скидку пользователю
        
        Args:
            user_id: telegram_id пользователя
            amount: размер скидки в процентах
            source: источник (wheel/referral/visit/content/cashback)
            lifetime_days: срок жизни в днях (по умолчанию 40)
            freeze_until: заморозить до даты
        
        Returns:
            Reward объект или None при ошибке
        """
        if lifetime_days is None:
            lifetime_days = DiscountEngine.DISCOUNT_LIFETIME_DAYS
        
        expires_at = datetime.utcnow() + timedelta(days=lifetime_days)
        
        # Проверка максимальной скидки по источнику
        if not await DiscountEngine._check_source_limit(user_id, amount, source):
            logger.warning(f"Превышен лимит по источнику {source} для user_id={user_id}")
            return None
        
        # Проверка общей максимальной скидки
        current_total = await DiscountEngine.get_available_discount(user_id)
        if current_total + amount > DiscountEngine.MAX_TOTAL_DISCOUNT:
            logger.warning(f"Превышен общий лимит скидки для user_id={user_id}")
            return None
        
        try:
            async with async_session() as session:
                reward = Reward(
                    user_id=user_id,
                    amount=amount,
                    source=source,
                    expires_at=expires_at,
                    is_frozen=bool(freeze_until),
                    freeze_until=freeze_until,
                )
                session.add(reward)
                await session.commit()
                await session.refresh(reward)
                
                logger.info(f"Добавлена скидка {amount}% пользователю {user_id} (источник: {source})")
                return reward
        except Exception as e:
            logger.error(f"Ошибка добавления скидки: {e}")
            return None
    
    @staticmethod
    async def _check_source_limit(user_id: int, new_amount: float, source: str) -> bool:
        """Проверка лимита по источнику"""
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.user_id == user_id,
                    Reward.source == source,
                    Reward.is_expired == False,
                    Reward.expires_at > datetime.utcnow(),
                )
            )
            current_source_rewards = result.scalars().all()
            current_total = sum(r.amount for r in current_source_rewards)
            
            limits = {
                "referral": DiscountEngine.MAX_REFERRAL_DISCOUNT,
                "content": DiscountEngine.MAX_CONTENT_DISCOUNT,
                "cashback": DiscountEngine.MAX_CASHBACK_DISCOUNT,
            }
            
            limit = limits.get(source, DiscountEngine.MAX_TOTAL_DISCOUNT)
            return (current_total + new_amount) <= limit
    
    @staticmethod
    async def get_available_discount(user_id: int) -> float:
        """
        Получить доступную скидку пользователя
        
        Учитывает:
        - Не истёкшие
        - Не замороженные
        - Лимит 15% если не было визитов
        - Лимит 40% максимум
        """
        async with async_session() as session:
            now = datetime.utcnow()
            
            # Активные не замороженные скидки
            result = await session.execute(
                select(Reward).where(
                    Reward.user_id == user_id,
                    Reward.expires_at > now,
                    Reward.is_expired == False,
                    Reward.is_frozen == False,
                )
            )
            active_rewards = result.scalars().all()
            total = sum(r.amount for r in active_rewards)
            
            # Ограничение 40%
            total = min(total, DiscountEngine.MAX_TOTAL_DISCOUNT)
            
            # Проверка визитов
            booking_result = await session.execute(
                select(Booking).where(
                    Booking.user_id == user_id,
                    Booking.status == "completed",
                )
            )
            has_visits = booking_result.scalar_one_or_none() is not None
            
            if not has_visits:
                total = min(total, DiscountEngine.MAX_DISCOUNT_WITHOUT_VISIT)
            
            return round(total, 2)
    
    @staticmethod
    async def get_user_discounts(user_id: int) -> list[Reward]:
        """Получить все скидки пользователя"""
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.user_id == user_id,
                ).order_by(Reward.created_at.desc())
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def freeze_discounts(user_id: int, booking_id: int, visit_date: datetime):
        """Заморозить скидки до даты визита"""
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.user_id == user_id,
                    Reward.is_expired == False,
                    Reward.is_frozen == False,
                    Reward.expires_at > datetime.utcnow(),
                )
            )
            rewards = result.scalars().all()
            
            now = datetime.utcnow()
            for reward in rewards:
                remaining = reward.expires_at - now
                reward.is_frozen = True
                reward.freeze_until = visit_date
                reward.frozen_at_booking_id = booking_id
                # Продлеваем срок жизни
                reward.expires_at = visit_date + remaining
            
            await session.commit()
            logger.info(f"Заморожено {len(rewards)} скидок для user_id={user_id}")
    
    @staticmethod
    async def unfreeze_discounts(user_id: int, booking_id: int):
        """Разморозить скидки после визита"""
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.user_id == user_id,
                    Reward.frozen_at_booking_id == booking_id,
                    Reward.is_frozen == True,
                )
            )
            rewards = result.scalars().all()
            
            for reward in rewards:
                reward.is_frozen = False
                reward.freeze_until = None
            
            await session.commit()
            logger.info(f"Разморожено {len(rewards)} скидок для user_id={user_id}")
    
    @staticmethod
    async def expire_old_discounts():
        """Пометить истёкшие скидки (cron job)"""
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.is_expired == False,
                    Reward.is_frozen == False,
                    Reward.expires_at <= datetime.utcnow(),
                )
            )
            expired_rewards = result.scalars().all()
            
            for reward in expired_rewards:
                reward.is_expired = True
            
            if expired_rewards:
                await session.commit()
                logger.info(f"Помечено как истёкшие {len(expired_rewards)} скидок")
