import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, WEBHOOK_URL, REDIS_URL
from database.models import Base
from database.db import engine
from celery_app.celery import init_celery

# Импорт всех хендлеров
from bot.handlers import (
    admin, user, referrals, gamification, lottery, shop,
    missions, rating, instagram, webapp, business, ai_assistant, reviews
)

# Импорт роутеров веб-админки
from web.routers import (
    admin_router, business_router, analytics_router,
    export_router, dashboard_router, booking_router
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery (для фоновых задач)
celery_app = init_celery()

# Telegram бот
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация всех обработчиков
admin.register_handlers(dp)
user.register_handlers(dp)
referrals.register_handlers(dp)
gamification.register_handlers(dp)
lottery.register_handlers(dp)
shop.register_handlers(dp)
missions.register_handlers(dp)
rating.register_handlers(dp)
instagram.register_handlers(dp)
webapp.register_handlers(dp)
business.register_handlers(dp)
ai_assistant.register_handlers(dp)
reviews.register_handlers(dp)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Установка вебхука Telegram
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    yield

    # Завершение работы
    await bot.delete_webhook()
    await dp.storage.close()
    await engine.dispose()

# FastAPI приложение
app = FastAPI(title="Growth Bot PRO", lifespan=lifespan)

# Монтирование статики и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/webapp", StaticFiles(directory="static/webapp", html=True), name="webapp")
templates = Jinja2Templates(directory="web/templates")

# Подключение веб-роутеров
app.include_router(admin_router, prefix="/admin")
app.include_router(business_router, prefix="/business")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(export_router, prefix="/export")
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(booking_router, prefix="/api")

# Webhook для Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    await dp.process_update(update)
    return {"status": "ok"}

# Health check для Railway / UptimeRobot
@app.get("/health")
async def health():
    return {"status": "ok"}

# Корневая страница → редирект на логин админки
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
