from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

# Асинхронный движок
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # True для отладки SQL
    pool_size=20,
    max_overflow=10,
)

# Фабрика сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """Получить асинхронную сессию"""
    async with async_session() as session:
        yield session


async def init_db():
    """Создать все таблицы (ВРЕМЕННО с пересозданием)"""
    async with engine.begin() as conn:
        # ВНИМАНИЕ: удалит все данные! Только для однократного исправления структуры.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Удалить все таблицы (осторожно!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
