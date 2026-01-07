"""Base model configuration and database setup."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


# Custom type annotations for common column types
uuid_pk = Annotated[
    str,
    mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    ),
]

created_at_column = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    ),
]

updated_at_column = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    ),
]


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[created_at_column]
    updated_at: Mapped[updated_at_column]


# Database engine and session
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
