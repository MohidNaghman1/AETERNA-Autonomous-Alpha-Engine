import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Get SYNC and ASYNC URLs if present
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")

# 2. If not present, build from DATABASE_URL or individual parts
if not SYNC_DATABASE_URL:
    # Try DATABASE_URL (should be sync/psycopg2 style)
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        SYNC_DATABASE_URL = DATABASE_URL
    else:
        # Build from parts (encode password)
        raw_password = os.getenv("POSTGRES_PASSWORD", "")
        encoded_password = urllib.parse.quote_plus(raw_password)
        POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        SYNC_DATABASE_URL = (
            f"postgresql+psycopg2://{POSTGRES_USER}:{encoded_password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )

# 3. Build ASYNC_DATABASE_URL if not set, using conversion logic
if not ASYNC_DATABASE_URL:
    if SYNC_DATABASE_URL.startswith("postgres://"):
        ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif SYNC_DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif SYNC_DATABASE_URL.startswith("postgresql+psycopg2://"):
        ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    else:
        ASYNC_DATABASE_URL = SYNC_DATABASE_URL  # fallback

# 4. Create async engine and session
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
Base = declarative_base()
