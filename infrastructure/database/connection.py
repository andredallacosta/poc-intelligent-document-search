import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        # Create async engine with optimized settings
        if settings.debug:
            # Debug mode: use NullPool (no pooling)
            self._engine = create_async_engine(
                settings.database_url,
                echo=False,
                poolclass=NullPool,
                pool_pre_ping=True,
            )
        else:
            # Production mode: use connection pooling
            self._engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        self._initialized = True
        logger.info("Database connection initialized")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._initialized:
            self.initialize()

        async with self._session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")


# Global database connection instance
db_connection = DatabaseConnection()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in db_connection.get_session():
        yield session


def get_async_session():
    """
    Retorna um context manager para sessão assíncrona
    Para uso em workers e jobs
    """
    if not db_connection._initialized:
        db_connection.initialize()

    return db_connection._session_factory()
