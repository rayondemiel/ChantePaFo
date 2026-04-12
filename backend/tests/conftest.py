import os

# Required settings must be present before `app.main` imports run.
os.environ.setdefault(
    "CHANTEPAFO_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault(
    "CHANTEPAFO_REDIS_URL",
    "redis://localhost:6379",
)
os.environ.setdefault(
    "CHANTEPAFO_SECRET_KEY",
    "test-secret-must-be-at-least-32-characters-long-abcdef",
)
os.environ.setdefault(
    "CHANTEPAFO_METRICS_PASSWORD",
    "test-metrics-password-long-enough-for-tests",
)

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db, get_redis  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client(db_session, fake_redis):
    async def override_db():
        yield db_session

    async def override_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def authed_client(client):
    resp = await client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password1"},
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    client.headers = dict(client.headers)
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.headers.pop("Authorization", None)
