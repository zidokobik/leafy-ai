from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from ..settings import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
	settings = get_settings()
	return create_async_engine(settings.DATABASE_URI.get_secret_value())


async def _async_database_session():
	engine = get_engine()
	async with AsyncSession(engine, expire_on_commit=False) as session:
		yield session


AsyncDatabaseSession = Annotated[AsyncSession, Depends(_async_database_session)]
