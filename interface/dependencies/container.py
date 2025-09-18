from functools import lru_cache

# FastAPI Dependencies
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.interfaces.llm_service import LLMServiceInterface
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from infrastructure.config.settings import settings
from infrastructure.database.connection import db_connection, get_db_session
from infrastructure.external.llm_service_impl import LLMServiceImpl
from infrastructure.external.openai_client import OpenAIClient
from infrastructure.external.redis_client import RedisClient
from infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentChunkRepository,
    PostgresDocumentRepository,
)
from infrastructure.repositories.postgres_prefeitura_repository import (
    PostgresPrefeituraRepository,
)
from infrastructure.repositories.postgres_session_repository import (
    PostgresMessageRepository,
    PostgresSessionRepository,
)
from infrastructure.repositories.postgres_usuario_repository import (
    PostgresUsuarioRepository,
)
from infrastructure.repositories.postgres_vector_repository import (
    PostgresVectorRepository,
)
from infrastructure.repositories.redis_session_repository import (
    RedisMessageRepository,
    RedisSessionRepository,
)


class Container:
    def __init__(self):
        self._instances = {}

    @lru_cache(maxsize=1)
    def get_openai_client(self) -> OpenAIClient:
        if "openai_client" not in self._instances:
            self._instances["openai_client"] = OpenAIClient(
                api_key=settings.openai_api_key
            )
        return self._instances["openai_client"]

    @lru_cache(maxsize=1)
    def get_redis_client(self) -> RedisClient:
        if "redis_client" not in self._instances:
            self._instances["redis_client"] = RedisClient(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
            )
        return self._instances["redis_client"]

    def get_db_session(self):
        """Retorna sessão PostgreSQL"""
        return get_db_session()

    @lru_cache(maxsize=1)
    def get_llm_service(self) -> LLMServiceInterface:
        if "llm_service" not in self._instances:
            self._instances["llm_service"] = LLMServiceImpl(
                openai_client=self.get_openai_client()
            )
        return self._instances["llm_service"]

    @lru_cache(maxsize=1)
    def get_session_repository(self) -> RedisSessionRepository:
        if "session_repository" not in self._instances:
            self._instances["session_repository"] = RedisSessionRepository(
                redis_client=self.get_redis_client()
            )
        return self._instances["session_repository"]

    @lru_cache(maxsize=1)
    def get_message_repository(self) -> RedisMessageRepository:
        if "message_repository" not in self._instances:
            self._instances["message_repository"] = RedisMessageRepository(
                redis_client=self.get_redis_client()
            )
        return self._instances["message_repository"]

    @lru_cache(maxsize=1)
    def get_chat_service(self) -> ChatService:
        if "chat_service" not in self._instances:
            self._instances["chat_service"] = ChatService(
                session_repository=self.get_session_repository(),
                message_repository=self.get_message_repository(),
                max_messages_per_session=settings.max_messages_per_session,
                max_daily_messages=settings.max_daily_messages,
            )
        return self._instances["chat_service"]

    async def close_connections(self):
        """Fecha todas as conexões"""
        if "redis_client" in self._instances:
            await self._instances["redis_client"].close()

        # Fecha conexão PostgreSQL
        await db_connection.close()


# Global container instance
container = Container()


# PostgreSQL Repository Dependencies


async def get_postgres_vector_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresVectorRepository:
    """Dependency para PostgresVectorRepository"""
    return PostgresVectorRepository(session)


async def get_postgres_document_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresDocumentRepository:
    """Dependency para PostgresDocumentRepository"""
    return PostgresDocumentRepository(session)


async def get_postgres_document_chunk_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresDocumentChunkRepository:
    """Dependency para PostgresDocumentChunkRepository"""
    return PostgresDocumentChunkRepository(session)


async def get_postgres_prefeitura_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresPrefeituraRepository:
    """Dependency para PostgresPrefeituraRepository"""
    return PostgresPrefeituraRepository(session)


async def get_postgres_usuario_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresUsuarioRepository:
    """Dependency para PostgresUsuarioRepository"""
    return PostgresUsuarioRepository(session)


async def get_postgres_session_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresSessionRepository:
    """Dependency para PostgresSessionRepository"""
    return PostgresSessionRepository(session)


async def get_postgres_message_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresMessageRepository:
    """Dependency para PostgresMessageRepository"""
    return PostgresMessageRepository(session)


def get_llm_service() -> LLMServiceInterface:
    return container.get_llm_service()


def get_chat_service() -> ChatService:
    return container.get_chat_service()


async def get_search_service(
    vector_repo: PostgresVectorRepository = Depends(get_postgres_vector_repository),
) -> SearchService:
    """Dependency para SearchService com PostgreSQL"""
    return SearchService(vector_repository=vector_repo)


async def get_chat_use_case(
    chat_service: ChatService = Depends(get_chat_service),
    search_service: SearchService = Depends(get_search_service),
    llm_service: LLMServiceInterface = Depends(get_llm_service),
) -> ChatWithDocumentsUseCase:
    """Dependency para ChatWithDocumentsUseCase com PostgreSQL"""
    return ChatWithDocumentsUseCase(
        chat_service=chat_service,
        search_service=search_service,
        llm_service=llm_service,
    )
