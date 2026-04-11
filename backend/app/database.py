from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as redis

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


class Base(DeclarativeBase):
    pass


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
