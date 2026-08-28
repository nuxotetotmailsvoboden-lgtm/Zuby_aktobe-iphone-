import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from config import settings
from db.base import init_db
from web_server import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    storage = RedisStorage(redis=redis)
    
    # ✅ ИСПРАВЛЕНО
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    
    dp = Dispatcher(storage=storage)
    
    import web_server
    web_server.bot = bot
    
    from middlewares.antiflood import AntiFloodMiddleware
    from middlewares.save_activity import SaveActivityMiddleware
    
    dp.message.middleware(AntiFloodMiddleware())
    dp.callback_query.middleware(AntiFloodMiddleware())
    dp.message.middleware(SaveActivityMiddleware())
    dp.callback_query.middleware(SaveActivityMiddleware())
    
    await init_db()
    logger.info("База данных инициализирована")
    
    from services.booking_service import BookingService
    await BookingService.generate_week_schedule()
    logger.info("Расписание сгенерировано")
    
    from handlers.start import router as start_router
    from handlers.main_menu import router as menu_router
    from handlers.wheel import router as wheel_router
    from handlers.booking import router as booking_router
    from handlers.content import router as content_router
    from handlers.raffle import router as raffle_router
    from handlers.admin import router as admin_router
    from handlers.broadcast import router as broadcast_router
    from handlers.cashback import router as cashback_router
    
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(broadcast_router)
    dp.include_router(menu_router)
    dp.include_router(wheel_router)
    dp.include_router(booking_router)
    dp.include_router(content_router)
    dp.include_router(raffle_router)
    dp.include_router(cashback_router)
    
    from services.notifications import run_scheduler
    scheduler = await run_scheduler(bot)
    
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(settings.PORT) if settings.PORT else 8080
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info("🦷 БОТ ЗАПУЩЕН!")
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await runner.cleanup()
        await bot.session.close()
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
