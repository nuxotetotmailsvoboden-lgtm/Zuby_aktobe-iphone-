import logging
from datetime import datetime, timedelta
from sqlalchemy import select

from db.base import async_session
from db.models import User, LogAction, Referral, Booking
from config import settings

logger = logging.getLogger(__name__)


class AntiFraudService:
    """Антифрод-сервис для оценки пользователей"""
    
    SCORE_ACTIONS = {
        "visit": +20,
        "booking": +10,
        "activity": +5,
        "instagram_subscribed": +5,
        "content_approved": +10,
        "multiaccount_suspect": -30,
        "suspicious_referral": -20,
        "no_actions_30days": -15,
        "shadow_ban_applied": -50,
    }
    
    @staticmethod
    async def get_multiplier(telegram_id: int) -> float:
        """Получить множитель для колеса и наград"""
        score = await AntiFraudService.get_score(telegram_id)
        if score >= 80:
            return 1.0
        elif score >= 50:
            return 0.5
        else:
            return 0.2
    
    @staticmethod
    async def get_score(telegram_id: int) -> int:
        """Получить текущий fraud_score пользователя"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return 100
            return user.fraud_score
    
    @staticmethod
    async def update_score(telegram_id: int, action: str) -> int:
        """Обновить fraud_score пользователя"""
        points = AntiFraudService.SCORE_ACTIONS.get(action, 0)
        if points == 0:
            return await AntiFraudService.get_score(telegram_id)
        
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                logger.warning(f"Попытка обновить счёт для несуществующего пользователя {telegram_id}")
                return 100
            
            old_score = user.fraud_score
            new_score = max(0, min(100, old_score + points))
            user.fraud_score = new_score
            
            # ✅ Исправлено: логируем с user.id, а не telegram_id
            log = LogAction(
                user_id=user.id,
                action=f"fraud_{action}",
                details=f"Score: {old_score} → {new_score} ({points:+d})",
            )
            session.add(log)
            await session.commit()
            
            logger.info(f"Fraud score user_id={user.id}: {old_score} → {new_score} (action: {action})")
            
            if new_score <= 30 and not user.shadow_ban:
                await AntiFraudService.apply_shadowban(telegram_id)
            
            return new_score
    
    @staticmethod
    async def apply_shadowban(telegram_id: int):
        """Применить теневой бан"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.shadow_ban = True
                user.fraud_score = max(0, user.fraud_score - 50)
                
                # ✅ Исправлено
                log = LogAction(
                    user_id=user.id,
                    action="shadow_ban",
                    details="Пользователь получил теневой бан",
                )
                session.add(log)
                await session.commit()
                
                logger.warning(f"Shadow ban applied to user_id={user.id}")
    
    @staticmethod
    async def detect_multiaccounts(telegram_id: int) -> bool:
        """Проверка на мультиаккаунты"""
        async with async_session() as session:
            refs_result = await session.execute(
                select(Referral).where(Referral.referrer_id == telegram_id)
            )
            refs = refs_result.scalars().all()
            if len(refs) > 10:
                recent_refs = [r for r in refs if (datetime.utcnow() - r.created_at).days < 1]
                if len(recent_refs) > 5:
                    await AntiFraudService.update_score(telegram_id, "suspicious_referral")
                    return True
            return False
    
    @staticmethod
    async def check_inactive_users():
        """Проверка неактивных пользователей (cron job)"""
        async with async_session() as session:
            threshold = datetime.utcnow() - timedelta(days=30)
            result = await session.execute(
                select(User).where(
                    User.last_activity < threshold,
                    User.fraud_score > 50,
                    User.shadow_ban == False,
                )
            )
            inactive_users = result.scalars().all()
            for user in inactive_users:
                await AntiFraudService.update_score(user.telegram_id, "no_actions_30days")
            logger.info(f"Обработано {len(inactive_users)} неактивных пользователей")
