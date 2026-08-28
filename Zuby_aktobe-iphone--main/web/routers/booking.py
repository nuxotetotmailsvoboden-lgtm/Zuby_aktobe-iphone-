from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from database.db import AsyncSessionLocal
from database.models import User, Booking, PointsHistory
from bot.config import ADMIN_IDS, BOT_TOKEN
from aiogram import Bot

router = APIRouter()

class BookingRequest(BaseModel):
    user_id: int
    service_id: int
    service_name: str
    amount: float
    name: str
    phone: str
    date: str
    time: str

@router.post("/create_booking")
async def create_booking(req: BookingRequest):
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, req.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")

            # Создаём запись в БД
            booking = Booking(
                user_id=req.user_id,
                business_id=user.business_id or 1,   # если бизнес не выбран, по умолчанию 1
                service=f"{req.service_name} (#{req.service_id})",
                amount=req.amount,
                status="pending",                     # ожидает подтверждения администратором
                created_at=datetime.now()
            )
            session.add(booking)

            # Начисляем небольшой бонус за заявку (опционально)
            bonus_points = 20
            user.points += bonus_points
            session.add(PointsHistory(
                user_id=user.id,
                points=bonus_points,
                reason=f"Заявка на запись {req.date} {req.time}"
            ))

            await session.commit()

            # Отправляем уведомление всем админам
            bot = Bot(token=BOT_TOKEN)
            text = f"""
🆕 <b>Новая заявка на запись</b>
👤 {req.name} (@{user.username or 'нет'})
📞 {req.phone}
🛠 Услуга: {req.service_name}
💵 Стоимость: {req.amount} ₸
📅 {req.date} в {req.time}
"""
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text, parse_mode="HTML")
                except:
                    pass

            # Уведомление пользователю
            try:
                await bot.send_message(req.user_id, f"✅ Ваша заявка на {req.date} в {req.time} принята. Администратор свяжется с вами.")
            except:
                pass

            await bot.session.close()

        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
