from celery import Celery
from bot.config import REDIS_URL

def init_celery():
    """Инициализация Celery приложения"""
    app = Celery(
        'growth_bot',
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=['celery_app.tasks']
    )
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Almaty',  # или Europe/Moscow
        enable_utc=True,
        beat_schedule={
            # Автоматический розыгрыш каждый час (можно изменить)
            'draw-lottery-every-hour': {
                'task': 'celery_app.tasks.draw_lottery_winners',
                'schedule': 3600.0,  # секунды
            },
        }
    )
    return app
