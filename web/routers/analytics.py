from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from database.db import get_db
from database.models import User, PointsHistory, Booking
from web.auth import authenticate_admin

router = APIRouter()
security = HTTPBasic()

@router.get("/registrations")
async def registrations_chart(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        dates = [(datetime.now() - timedelta(days=i)).date() for i in range(6, -1, -1)]
        counts = []
        for d in dates:
            cnt = await session.scalar(
                select(func.count()).where(func.date(User.registered_at) == d)
            )
            counts.append(cnt)
        return {"dates": [str(d) for d in dates], "counts": counts}

@router.get("/activity")
async def activity_chart(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        dates = [(datetime.now() - timedelta(days=i)).date() for i in range(6, -1, -1)]
        points = []
        for d in dates:
            total = await session.scalar(
                select(func.sum(PointsHistory.points)).where(
                    and_(
                        func.date(PointsHistory.created_at) == d,
                        PointsHistory.points > 0
                    )
                )
            ) or 0
            points.append(total)
        return {"dates": [str(d) for d in dates], "points": points}

@router.get("/bookings")
async def bookings_chart(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        dates = [(datetime.now() - timedelta(days=i)).date() for i in range(6, -1, -1)]
        counts = []
        revenue = []
        for d in dates:
            cnt = await session.scalar(
                select(func.count()).where(func.date(Booking.created_at) == d)
            )
            rev = await session.scalar(
                select(func.sum(Booking.amount)).where(
                    and_(
                        func.date(Booking.created_at) == d,
                        Booking.status == "completed"
                    )
                )
            ) or 0
            counts.append(cnt)
            revenue.append(float(rev))
        return {"dates": [str(d) for d in dates], "counts": counts, "revenue": revenue}
