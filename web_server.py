from aiohttp import web
import logging

logger = logging.getLogger(__name__)

bot = None  # Храним объект Bot


async def health_check(request):
    return web.Response(text="OK", status=200)


async def bot_info(request):
    if bot is None:
        return web.json_response({"status": "bot not initialized"})
    
    try:
        me = await bot.get_me()
        return web.json_response({
            "status": "running",
            "bot_username": me.username,
            "bot_id": me.id,
        })
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})


def create_web_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/ping", health_check)
    app.router.add_get("/bot/info", bot_info)
    return app
