from fastapi import APIRouter, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from web.auth import authenticate_admin

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")
security = HTTPBasic()

@router.get("/")
async def dashboard(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    await authenticate_admin(credentials.username, credentials.password)
    return templates.TemplateResponse("dashboard.html", {"request": request})
