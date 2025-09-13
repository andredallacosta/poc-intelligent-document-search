from functools import lru_cache

from application.interfaces.llm_service import LLMServiceInterface
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from domain.services.chat_service import ChatService
from domain.services.search_service import SearchService
from infrastructure.config.settings import settings
from infrastructure.external.openai_client import OpenAIClient
from infrastructure.external.redis_client import RedisClient
from infrastructure.external.chroma_client import ChromaClient
from infrastructure.external.llm_service_impl import LLMServiceImpl
from infrastructure.repositories.redis_session_repository import (
    RedisSessionRepository, 
    RedisMessageRepository
)
from infrastructure.repositories.chroma_vector_repository import ChromaVectorRepository


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
                password=settings.redis_password
            )
        return self._instances["redis_client"]
    
    @lru_cache(maxsize=1)
    def get_chroma_client(self) -> ChromaClient:
        if "chroma_client" not in self._instances:
            self._instances["chroma_client"] = ChromaClient(
                persist_directory=settings.chroma_persist_directory,
                collection_name=settings.chroma_collection_name
            )
        return self._instances["chroma_client"]
    
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
    def get_vector_repository(self) -> ChromaVectorRepository:
        if "vector_repository" not in self._instances:
            self._instances["vector_repository"] = ChromaVectorRepository(
                chroma_client=self.get_chroma_client()
            )
        return self._instances["vector_repository"]
    
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
        if "redis_client" in self._instances:
            await self._instances["redis_client"].close()


# Global container instance
container = Container()


# Dependency functions for FastAPI
def get_chat_use_case() -> ChatWithDocumentsUseCase:
    return container.get_chat_use_case()


def get_llm_service() -> LLMServiceInterface:
    return container.get_llm_service()


def get_chat_service() -> ChatService:
    return container.get_chat_service()


def get_search_service() -> SearchService:
    return container.get_search_service()
