from datetime import date, time, datetime, timedelta
from typing import Optional, List, Tuple
import logging

from sqlalchemy import select, and_, or_
from db.base import async_session
from db.models import Booking, Schedule, User
from utils.validators import add_minutes

logger = logging.getLogger(__name__)


class SlotBusyException(Exception):
    def __init__(self, message: str, alternative_date: Optional[date] = None, alternative_time: Optional[time] = None):
        self.message = message
        self.alternative_date = alternative_date
        self.alternative_time = alternative_time
        super().__init__(message)


class BookingService:
    
    WORKING_HOURS = [
        (time(9, 0), time(13, 0)),
        (time(14, 0), time(18, 0)),
    ]
    
    SLOT_INTERVAL = 30
    MAX_DAYS_AHEAD = 14
    
    @classmethod
    async def get_available_slots(cls, check_date: date, service_duration: int = 60) -> List[time]:
        """Генерирует слоты НА ЛЕТУ, без таблицы schedule"""
        async with async_session() as session:
            # Получаем все подтверждённые записи на эту дату
            bookings_result = await session.execute(
                select(Booking).where(
                    Booking.date == check_date,
                    Booking.status.in_(["confirmed", "pending"]),
                    Booking.slot_booked == True,
                )
            )
            booked_slots = bookings_result.scalars().all()
        
        available_slots = []
        
        # Перебираем рабочие часы с интервалом 30 минут
        for start_h, end_h in cls.WORKING_HOURS:
            current_time = start_h
            while current_time < end_h:
                end_slot_time = add_minutes(current_time, service_duration)
                
                if end_slot_time > end_h:
                    current_time = add_minutes(current_time, cls.SLOT_INTERVAL)
                    continue
                
                # Проверяем пересечение с занятыми слотами
                is_free = True
                for booking in booked_slots:
                    booking_end = add_minutes(booking.time, booking.duration)
                    if current_time < booking_end and end_slot_time > booking.time:
                        is_free = False
                        break
                
                if is_free:
                    available_slots.append(current_time)
                
                current_time = add_minutes(current_time, cls.SLOT_INTERVAL)
        
        logger.info(f"Слоты для {check_date} (длит. {service_duration}мин): {len(available_slots)}")
        return available_slots
    
    @classmethod
    async def get_available_dates(cls, service_duration: int = 60, days_ahead: int = None) -> List[date]:
        if days_ahead is None:
            days_ahead = cls.MAX_DAYS_AHEAD
        
        available_dates = []
        today = date.today()
        
        for day_offset in range(days_ahead + 1):
            check_date = today + timedelta(days=day_offset)
            if check_date.weekday() == 6:  # воскресенье
                continue
            slots = await cls.get_available_slots(check_date, service_duration)
            if slots:
                available_dates.append(check_date)
        
        return available_dates
    
    @classmethod
    async def book_slot(cls, user_id: int, service: str, service_duration: int, booking_date: date, booking_time: time, comment: str = None) -> Booking:
        async with async_session() as session:
            # Повторная проверка
            booked = await session.execute(
                select(Booking).where(
                    Booking.date == booking_date,
                    Booking.status.in_(["confirmed", "pending"]),
                    Booking.slot_booked == True,
                )
            )
            booked_slots = booked.scalars().all()
            
            end_time = add_minutes(booking_time, service_duration)
            
            for existing in booked_slots:
                existing_end = add_minutes(existing.time, existing.duration)
                if booking_time < existing_end and end_time > existing.time:
                    alternative = await cls.find_nearest_available(booking_date, booking_time, service_duration)
                    raise SlotBusyException(
                        f"Время {booking_time.strftime('%H:%M')} занято",
                        alternative_date=alternative[0] if alternative else None,
                        alternative_time=alternative[1] if alternative else None,
                    )
            
            booking = Booking(
                user_id=user_id,
                service=service,
                date=booking_date,
                time=booking_time,
                duration=service_duration,
                comment=comment,
                status="confirmed",
                slot_booked=True,
                confirmed_at=datetime.utcnow(),
            )
            session.add(booking)
            
            user_result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                user.last_activity = datetime.utcnow()
            
            await session.commit()
            await session.refresh(booking)
            
            logger.info(f"Бронь создана: user_id={user_id}, {booking_date} {booking_time}")
            return booking
    
    @classmethod
    async def find_nearest_available(cls, from_date: date, from_time: time, service_duration: int, max_search_days: int = 7) -> Optional[Tuple[date, time]]:
        # Ищем в этот же день
        same_day_slots = await cls.get_available_slots(from_date, service_duration)
        for slot in same_day_slots:
            if slot > from_time:
                return (from_date, slot)
        
        # Ищем в следующие дни
        for day_offset in range(1, max_search_days + 1):
            check_date = from_date + timedelta(days=day_offset)
            if check_date.weekday() == 6:
                continue
            slots = await cls.get_available_slots(check_date, service_duration)
            if slots:
                return (check_date, slots[0])
        
        return None
    
    @classmethod
    async def confirm_visit(cls, booking_id: int, admin_id: int):
        async with async_session() as session:
            result = await session.execute(select(Booking).where(Booking.id == booking_id))
            booking = result.scalar_one_or_none()
            if booking:
                booking.status = "completed"
                booking.completed_at = datetime.utcnow()
                
                user_result = await session.execute(select(User).where(User.telegram_id == booking.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.total_visits += 1
                
                await session.commit()
    
    @classmethod
    async def get_user_bookings(cls, user_id: int) -> List[Booking]:
        async with async_session() as session:
            result = await session.execute(
                select(Booking).where(Booking.user_id == user_id).order_by(Booking.date.desc(), Booking.time.desc())
            )
            return list(result.scalars().all())
    
    @classmethod
    async def generate_week_schedule(cls, start_date: date = None):
        """Пустая заглушка — слоты генерируются на лету"""
        logger.info("Расписание не требуется — слоты генерируются динамически")
