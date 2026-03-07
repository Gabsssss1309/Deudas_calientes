"""
Async database engine + session factory.
Uses the same Supabase PostgreSQL as the Next.js app.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import config

engine = create_async_engine(config.database_url, echo=False)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    """Yield a fresh async session."""
    async with async_session() as session:
        yield session
