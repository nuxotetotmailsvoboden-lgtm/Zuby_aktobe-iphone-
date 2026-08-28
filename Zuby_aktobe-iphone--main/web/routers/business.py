from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import select
from database.db import get_db
from database.models import Business
from web.auth import authenticate_admin

router = APIRouter()
security = HTTPBasic()

class BusinessCreate(BaseModel):
    name: str
    owner_id: int

class BusinessUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None

@router.get("/list")
async def list_businesses(credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        businesses = (await session.execute(
            select(Business).order_by(Business.created_at.desc())
        )).scalars().all()

        return [
            {
                "id": b.id,
                "name": b.name,
                "owner_id": b.owner_id,
                "is_active": b.is_active,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in businesses
        ]

@router.post("/create")
async def create_business(data: BusinessCreate, credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        business = Business(name=data.name, owner_id=data.owner_id)
        session.add(business)
        await session.commit()
        return {"status": "ok", "id": business.id}

@router.post("/{business_id}/update")
async def update_business(business_id: int, data: BusinessUpdate, credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)

    async for session in get_db():
        business = await session.get(Business, business_id)
        if not business:
            raise HTTPException(404, "Business not found")
        if data.name is not None:
            business.name = data.name
        if data.is_active is not None:
            business.is_active = data.is_active
        await session.commit()
        return {"status": "ok"}
