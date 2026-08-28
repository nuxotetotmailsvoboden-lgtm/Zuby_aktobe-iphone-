from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from bot.config import DATABASE_URL

# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False)

# Фабрика сессий для работы с БД
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Генератор асинхронной сессии БД"""
    async with AsyncSessionLocal() as session:
        yield session
