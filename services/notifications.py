import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_

from db.base import async_session
from db.models import Reward, Booking, User
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис уведомлений"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def check_expiring_discounts(self):
        """Проверка скидок, которые скоро сгорят"""
        logger.info("Проверка сгорающих скидок...")
        
        now = datetime.utcnow()
        
        check_periods = [
            (3, "3 дня"),
            (1, "1 день"),
            (0, "сегодня"),
        ]
        
        async with async_session() as session:
            for days, period_text in check_periods:
                target_date = now + timedelta(days=days)
                start_of_day = target_date.replace(hour=0, minute=0, second=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59)
                
                result = await session.execute(
                    select(Reward).where(
                        Reward.expires_at.between(start_of_day, end_of_day),
                        Reward.is_expired == False,
                        Reward.is_frozen == False,
                    )
                )
                expiring_rewards = result.scalars().all()
                
                for reward in expiring_rewards:
                    try:
                        await self.bot.send_message(
                            reward.user_id,
                            f"⏳ <b>Скидка {reward.amount}% скоро сгорит!</b>\n\n"
                            f"📅 Осталось: <b>{period_text}</b>\n"
                            f"🎁 Источник: {reward.source}\n\n"
                            f"💡 <b>Запишитесь на приём сейчас</b>, чтобы заморозить скидку!\n"
                            f"После записи скидка не сгорит до визита.",
                            parse_mode="HTML"
                        )
                        logger.info(f"Уведомление о сгорании скидки отправлено user_id={reward.user_id}")
                    except Exception as e:
                        logger.error(f"Не удалось отправить уведомление user_id={reward.user_id}: {e}")
    
    async def check_booking_reminders(self):
        """Проверка напоминаний о записи за 2 часа"""
        logger.info("Проверка напоминаний о записи...")
        
        now = datetime.utcnow()
        reminder_time = now + timedelta(hours=2)
        
        async with async_session() as session:
            result = await session.execute(
                select(Booking).where(
                    Booking.status == "confirmed",
                    Booking.date == reminder_time.date(),
                    Booking.time.between(
                        reminder_time.time(),
                        (reminder_time + timedelta(minutes=30)).time(),
                    ),
                )
            )
            upcoming_bookings = result.scalars().all()
            
            for booking in upcoming_bookings:
                try:
                    await self.bot.send_message(
                        booking.user_id,
                        f"⏰ <b>НАПОМИНАНИЕ О ЗАПИСИ</b>\n\n"
                        f"🦷 {booking.service}\n"
                        f"📅 {booking.date.strftime('%d.%m.%Y')}\n"
                        f"🕐 {booking.time.strftime('%H:%M')}\n\n"
                        f"Ждём вас через <b>2 часа</b>!\n\n"
                        f"📍 г. Актобе, ул. Примерная, д. 123\n"
                        f"📞 +7 (999) 123-45-67",
                        parse_mode="HTML"
                    )
                    logger.info(f"Напоминание о визите отправлено user_id={booking.user_id}")
                except Exception as e:
                    logger.error(f"Не удалось отправить напоминание user_id={booking.user_id}: {e}")
    
    async def expire_old_discounts(self):
        """Автоматическое истечение старых скидок"""
        logger.info("Проверка истёкших скидок...")
        
        async with async_session() as session:
            result = await session.execute(
                select(Reward).where(
                    Reward.expires_at <= datetime.utcnow(),
                    Reward.is_expired == False,
                    Reward.is_frozen == False,
                )
            )
            expired = result.scalars().all()
            
            count = 0
            for reward in expired:
                reward.is_expired = True
                count += 1
                
                try:
                    await self.bot.send_message(
                        reward.user_id,
                        f"💨 <b>Скидка {reward.amount}% сгорела</b>\n\n"
                        f"Источник: {reward.source}\n\n"
                        f"Не расстраивайтесь! Вы можете:\n"
                        f"🎰 Покрутить колесо фортуны\n"
                        f"👥 Пригласить друзей\n"
                        f"📸 Опубликовать контент\n\n"
                        f"И получить новую скидку!",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            if count > 0:
                await session.commit()
                logger.info(f"Помечено как истёкшие {count} скидок")
    
    async def check_inactive_users(self):
        """Проверка неактивных пользователей"""
        logger.info("Проверка неактивных пользователей...")
        
        from services.antifraud import AntiFraudService
        await AntiFraudService.check_inactive_users()
    
    async def send_daily_tip(self):
        """Отправить ежедневный совет всем активным пользователям"""
        logger.info("Отправка ежедневного совета...")
        
        from services.dental_tips import get_random_tip
        
        tip = get_random_tip()
        
        async with async_session() as session:
            threshold = datetime.utcnow() - timedelta(days=7)
            result = await session.execute(
                select(User.telegram_id).where(User.last_activity >= threshold)
            )
            active_users = result.scalars().all()
        
        success = 0
        failed = 0
        
        for user_id in active_users:
            try:
                await self.bot.send_message(
                    user_id,
                    f'🌅 <b>СОВЕТ ДНЯ</b>\n\n{tip}\n\n'
                    f'🦷 <i>С заботой о вашей улыбке, Zere Dent Aktobe</i>',
                    parse_mode='HTML'
                )
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"Не удалось отправить совет user_id={user_id}: {e}")
        
        logger.info(f"Совет дня отправлен: {success} успешно, {failed} ошибок")


async def run_scheduler(bot):
    """Запуск планировщика фоновых задач"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    notifier = NotificationService(bot)
    
    # Проверка сгорающих скидок — каждый час
    scheduler.add_job(
        notifier.check_expiring_discounts,
        'interval',
        hours=1,
        id='expiring_discounts',
    )
    
    # Напоминания о записи — каждые 15 минут
    scheduler.add_job(
        notifier.check_booking_reminders,
        'interval',
        minutes=15,
        id='booking_reminders',
    )
    
    # Истечение скидок — каждый час
    scheduler.add_job(
        notifier.expire_old_discounts,
        'interval',
        hours=1,
        id='expire_discounts',
    )
    
    # Проверка неактивных — раз в сутки
    scheduler.add_job(
        notifier.check_inactive_users,
        'interval',
        hours=24,
        id='inactive_check',
    )
    
    # Генерация расписания — раз в неделю
    from services.booking_service import BookingService
    scheduler.add_job(
        BookingService.generate_week_schedule,
        'interval',
        days=7,
        id='schedule_generation',
    )
    
    # ✅ Ежедневный совет в 10:00 — ТЕПЕРЬ ВНУТРИ ФУНКЦИИ
    scheduler.add_job(
        notifier.send_daily_tip,
        'cron',
        hour=10,
        minute=0,
        id='daily_tip',
    )
    
    scheduler.start()
    logger.info("Планировщик фоновых задач запущен")
    
    return scheduler
