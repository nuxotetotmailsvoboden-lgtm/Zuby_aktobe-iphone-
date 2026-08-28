from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, func
from database.db import get_db
from database.models import User, Business, Booking, PointsHistory, ReviewSubmission
from web.auth import authenticate_admin
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBasic()

@router.get("/stats")
async def get_stats(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        total_users = await session.scalar(select(func.count()).select_from(User))
        total_businesses = await session.scalar(select(func.count()).select_from(Business))
        total_bookings = await session.scalar(select(func.count()).select_from(Booking))
        total_revenue = await session.scalar(select(func.sum(Booking.amount)).where(Booking.status == "completed")) or 0

        # ROI – упрощённо: доход / (кол-во пользователей * 10) * 100 (пример)
        roi = round((total_revenue / (total_users * 10 + 1)) * 100, 2)

        return {
            "total_users": total_users,
            "total_businesses": total_businesses,
            "total_bookings": total_bookings,
            "total_revenue": float(total_revenue),
            "roi": roi
        }

@router.get("/recent_users")
async def recent_users(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        users = (await session.execute(
            select(User).order_by(User.registered_at.desc()).limit(10)
        )).scalars().all()

        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "username": u.username,
                "phone": u.phone,
                "points": u.points,
                "registered_at": u.registered_at.isoformat() if u.registered_at else None
            }
            for u in users
        ]

@router.get("/reviews")
async def list_reviews(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        reviews = (await session.execute(
            select(ReviewSubmission).order_by(ReviewSubmission.created_at.desc())
        )).scalars().all()

        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": r.user.username if r.user else "",
                "type": r.type,
                "content": r.content,
                "status": r.status,
                "created_at": r.created_at.isoformat()
            }
            for r in reviews
        ]

@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: int, credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        review = await session.get(ReviewSubmission, review_id)
        if not review:
            raise HTTPException(404, "Review not found")
        review.status = "approved"
        user = await session.get(User, review.user_id)
        if user:
            user.points += 200
            session.add(PointsHistory(user_id=user.id, points=200, reason="Видео-отзыв одобрен"))
        await session.commit()
    return {"status": "ok"}

@router.post("/reviews/{review_id}/reject")
async def reject_review(review_id: int, credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        review = await session.get(ReviewSubmission, review_id)
        if not review:
            raise HTTPException(404, "Review not found")
        review.status = "rejected"
        await session.commit()
    return {"status": "ok"}
