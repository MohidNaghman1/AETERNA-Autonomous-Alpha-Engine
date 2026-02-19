import os
from pathlib import Path
import pytest
from alembic.config import Config
from alembic import command
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app as fastapi_app
from app.shared.application.dependencies import get_db

import httpx
from httpx import ASGITransport

# Set up test DB URL (SQLite in-memory or file)
TEST_DB_PATH = "./test.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Set environment variable for Alembic and app config
os.environ["ASYNC_DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

BASE_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BASE_DIR / "alembic.ini"

@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    db_path = Path(TEST_DB_PATH)
    if db_path.exists():
        db_path.unlink()
    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{TEST_DB_PATH}")
    command.upgrade(alembic_cfg, "head")

# Create async engine and sessionmaker for test DB
engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Dependency override for FastAPI
async def override_get_db():
    async with AsyncTestingSessionLocal() as session:
        yield session

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
