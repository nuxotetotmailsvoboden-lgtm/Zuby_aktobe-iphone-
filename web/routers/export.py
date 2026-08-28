import csv
from io import StringIO
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, and_
from web.auth import authenticate_admin
from database.db import get_db
from database.models import User

router = APIRouter()
security = HTTPBasic()

@router.get("/users")
async def export_users(
    credentials: HTTPBasicCredentials = Depends(security),
    date_from: str = Query(None),
    date_to: str = Query(None),
    business_id: int = Query(None)
):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        query = select(User)
        filters = []
        if date_from:
            filters.append(User.registered_at >= datetime.fromisoformat(date_from))
        if date_to:
            filters.append(User.registered_at <= datetime.fromisoformat(date_to))
        if business_id:
            filters.append(User.business_id == business_id)
        if filters:
            query = query.where(and_(*filters))

        users = (await session.execute(query)).scalars().all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Username", "Full Name", "Phone", "Instagram", "Points", "Level", "Registered At"])
        for u in users:
            writer.writerow([
                u.id,
                u.username,
                u.full_name,
                u.phone,
                u.instagram,
                u.points,
                u.level,
                u.registered_at.isoformat() if u.registered_at else ""
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users.csv"}
        )
