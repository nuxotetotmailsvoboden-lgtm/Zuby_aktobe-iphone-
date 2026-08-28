from fastapi import HTTPException, status
import secrets
from bot.config import ADMIN_USERNAME, ADMIN_PASSWORD

async def authenticate_admin(username: str, password: str):
    """Проверяет логин и пароль администратора (Basic Auth)"""
    if not secrets.compare_digest(username, ADMIN_USERNAME) or \
       not secrets.compare_digest(password, ADMIN_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
