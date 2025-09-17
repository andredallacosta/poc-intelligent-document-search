from functools import lru_cache
from typing import AsyncGenerator

from application.interfaces.llm_service import LLMServiceInterface
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from infrastructure.config.settings import settings
from infrastructure.external.openai_client import OpenAIClient
from infrastructure.external.redis_client import RedisClient
from infrastructure.external.chroma_client import ChromaClient
from infrastructure.external.llm_service_impl import LLMServiceImpl

# PostgreSQL imports
from infrastructure.database.connection import db_connection, get_db_session
from infrastructure.repositories.postgres_prefeitura_repository import PostgresPrefeituraRepository
from infrastructure.repositories.postgres_usuario_repository import PostgresUsuarioRepository
from infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository, 
    PostgresDocumentChunkRepository
)
from infrastructure.repositories.postgres_vector_repository import PostgresVectorRepository
from infrastructure.repositories.postgres_session_repository import (
    PostgresSessionRepository, 
    PostgresMessageRepository
)

# Legacy imports (TEMPORÁRIO - será removido)
from infrastructure.repositories.redis_session_repository import (
    RedisSessionRepository, 
    RedisMessageRepository
)
from domain.repositories.vector_repository import VectorRepository
from domain.repositories.document_repository import DocumentRepository, DocumentChunkRepository
from domain.repositories.prefeitura_repository import PrefeituraRepository
from domain.repositories.usuario_repository import UsuarioRepository
from infrastructure.repositories.chroma_vector_repository import ChromaVectorRepository
from infrastructure.repositories.memory_document_repository import (
    MemoryDocumentRepository, 
    MemoryDocumentChunkRepository
)


class Container:
    def __init__(self):
        self._instances = {}
        self._use_postgres = True  # Flag para controlar qual implementação usar
    
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
                password=settings.redis_password
            )
        return self._instances["redis_client"]
    
    @lru_cache(maxsize=1)
    def get_chroma_client(self) -> ChromaClient:
        # TEMPORÁRIO - será removido após migração completa
        if "chroma_client" not in self._instances:
            self._instances["chroma_client"] = ChromaClient(
                persist_directory=settings.chroma_persist_directory,
                collection_name=settings.chroma_collection_name
            )
        return self._instances["chroma_client"]
    
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
    
    def get_vector_repository(self) -> VectorRepository:
        """Retorna repositório de vetores (PostgreSQL ou ChromaDB)"""
        if self._use_postgres:
            # Não pode usar @lru_cache porque precisa de sessão diferente a cada chamada
            # A sessão será gerenciada pelo FastAPI dependency injection
            return "postgres_vector_repository"  # Placeholder - será resolvido no FastAPI
        else:
            # Fallback para ChromaDB (TEMPORÁRIO)
            if "vector_repository" not in self._instances:
                self._instances["vector_repository"] = ChromaVectorRepository(
                    chroma_client=self.get_chroma_client()
                )
            return self._instances["vector_repository"]
    
    def get_document_repository(self) -> DocumentRepository:
        """Retorna repositório de documentos (PostgreSQL ou Memory)"""
        if self._use_postgres:
            return "postgres_document_repository"  # Placeholder - será resolvido no FastAPI
        else:
            # Fallback para Memory (TEMPORÁRIO)
            if "document_repository" not in self._instances:
                self._instances["document_repository"] = MemoryDocumentRepository()
            return self._instances["document_repository"]
    
    def get_document_chunk_repository(self) -> DocumentChunkRepository:
        """Retorna repositório de chunks (PostgreSQL ou Memory)"""
        if self._use_postgres:
            return "postgres_document_chunk_repository"  # Placeholder - será resolvido no FastAPI
        else:
            # Fallback para Memory (TEMPORÁRIO)
            if "document_chunk_repository" not in self._instances:
                self._instances["document_chunk_repository"] = MemoryDocumentChunkRepository()
            return self._instances["document_chunk_repository"]
    
    def get_prefeitura_repository(self) -> PrefeituraRepository:
        """Retorna repositório de prefeituras (PostgreSQL)"""
        return "postgres_prefeitura_repository"  # Placeholder - será resolvido no FastAPI
    
    def get_usuario_repository(self) -> UsuarioRepository:
        """Retorna repositório de usuários (PostgreSQL)"""
        return "postgres_usuario_repository"  # Placeholder - será resolvido no FastAPI
    
    @lru_cache(maxsize=1)
    def get_chat_service(self) -> ChatService:
        if "chat_service" not in self._instances:
            self._instances["chat_service"] = ChatService(
                session_repository=self.get_session_repository(),
                message_repository=self.get_message_repository(),
                max_messages_per_session=settings.max_messages_per_session,
                max_daily_messages=settings.max_daily_messages
            )
        return self._instances["chat_service"]
    
    @lru_cache(maxsize=1)
    def get_search_service(self) -> SearchService:
        if "search_service" not in self._instances:
            self._instances["search_service"] = SearchService(
                vector_repository=self.get_vector_repository()
            )
        return self._instances["search_service"]
    
    @lru_cache(maxsize=1)
    def get_chat_use_case(self) -> ChatWithDocumentsUseCase:
        if "chat_use_case" not in self._instances:
            self._instances["chat_use_case"] = ChatWithDocumentsUseCase(
                chat_service=self.get_chat_service(),
                search_service=self.get_search_service(),
                llm_service=self.get_llm_service()
            )
        return self._instances["chat_use_case"]
    
    async def close_connections(self):
        """Fecha todas as conexões"""
        if "redis_client" in self._instances:
            await self._instances["redis_client"].close()
        
        # Fecha conexão PostgreSQL
        await db_connection.close()


# Global container instance
container = Container()


# Dependency functions for FastAPI

# PostgreSQL Repository Dependencies
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


async def get_postgres_vector_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresVectorRepository:
    """Dependency para PostgresVectorRepository"""
    return PostgresVectorRepository(session)


async def get_postgres_document_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresDocumentRepository:
    """Dependency para PostgresDocumentRepository"""
    return PostgresDocumentRepository(session)


async def get_postgres_document_chunk_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresDocumentChunkRepository:
    """Dependency para PostgresDocumentChunkRepository"""
    return PostgresDocumentChunkRepository(session)


async def get_postgres_prefeitura_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresPrefeituraRepository:
    """Dependency para PostgresPrefeituraRepository"""
    return PostgresPrefeituraRepository(session)


async def get_postgres_usuario_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresUsuarioRepository:
    """Dependency para PostgresUsuarioRepository"""
    return PostgresUsuarioRepository(session)


async def get_postgres_session_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresSessionRepository:
    """Dependency para PostgresSessionRepository"""
    return PostgresSessionRepository(session)


async def get_postgres_message_repository(
    session: AsyncSession = Depends(get_db_session)
) -> PostgresMessageRepository:
    """Dependency para PostgresMessageRepository"""
    return PostgresMessageRepository(session)


# Legacy Dependencies (mantém compatibilidade)
def get_chat_use_case() -> ChatWithDocumentsUseCase:
    return container.get_chat_use_case()


def get_llm_service() -> LLMServiceInterface:
    return container.get_llm_service()


def get_chat_service() -> ChatService:
    return container.get_chat_service()


def get_search_service() -> SearchService:
    return container.get_search_service()


def get_document_repository() -> DocumentRepository:
    return container.get_document_repository()


def get_document_chunk_repository() -> DocumentChunkRepository:
    return container.get_document_chunk_repository()


# New Multi-tenancy Dependencies
def get_prefeitura_repository() -> PrefeituraRepository:
    return container.get_prefeitura_repository()


def get_usuario_repository() -> UsuarioRepository:
    return container.get_usuario_repository()
