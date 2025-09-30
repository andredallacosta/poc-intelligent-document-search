from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.interfaces.llm_service import LLMServiceInterface
from application.use_cases.chat_with_documents import ChatWithDocumentsUseCase
from application.use_cases.create_presigned_upload import CreatePresignedUploadUseCase
from application.use_cases.get_document_status import (
    GetDocumentStatusUseCase,
    GetJobStatusUseCase,
)
from application.use_cases.process_uploaded_document import (
    ProcessUploadedDocumentUseCase,
)
from domain.services.chat_service import ChatService
from domain.services.document_processor import DocumentProcessor
from domain.services.document_service import DocumentService
from domain.services.search_service import SearchService
from domain.services.threshold_service import ThresholdService
from infrastructure.config.settings import settings
from infrastructure.database.connection import db_connection, get_db_session
from infrastructure.external.llm_service_impl import LLMServiceImpl
from infrastructure.external.openai_client import OpenAIClient
from infrastructure.external.redis_client import RedisClient
from infrastructure.external.s3_service import S3Service
from infrastructure.processors.text_chunker import TextChunker
from infrastructure.repositories.postgres_document_processing_job_repository import (
    PostgresDocumentProcessingJobRepository,
)
from infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentChunkRepository,
    PostgresDocumentRepository,
)
from infrastructure.repositories.postgres_file_upload_repository import (
    PostgresFileUploadRepository,
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
            redis_url = (
                settings.get_redis_url()
                if hasattr(settings, "get_redis_url")
                else settings.redis_url
            )

            if redis_url:
                self._instances["redis_client"] = RedisClient(url=redis_url)
            else:
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

    @lru_cache(maxsize=1)
    def get_s3_service(self) -> S3Service:
        """Retorna S3Service configurado"""
        if "s3_service" not in self._instances:
            self._instances["s3_service"] = S3Service(
                bucket=getattr(settings, "s3_bucket", "documents"),
                region=getattr(settings, "s3_region", "us-east-1"),
                access_key=getattr(settings, "aws_access_key", None),
                secret_key=getattr(settings, "aws_secret_key", None),
                endpoint_url=getattr(settings, "s3_endpoint_url", None),
                public_endpoint_url=getattr(settings, "s3_public_endpoint_url", None),
            )
        return self._instances["s3_service"]

    @lru_cache(maxsize=1)
    def get_text_chunker(self) -> TextChunker:
        """Retorna TextChunker configurado"""
        if "text_chunker" not in self._instances:
            self._instances["text_chunker"] = TextChunker(
                chunk_size=getattr(settings, "chunk_size", 500),
                chunk_overlap=getattr(settings, "chunk_overlap", 50),
                use_contextual_retrieval=getattr(
                    settings, "use_contextual_retrieval", True
                ),
            )
        return self._instances["text_chunker"]

    @lru_cache(maxsize=1)
    def get_document_service(self) -> DocumentService:
        """Retorna DocumentService"""
        return None

    @lru_cache(maxsize=1)
    def get_document_processor(self) -> DocumentProcessor:
        """Retorna DocumentProcessor configurado"""
        if "document_processor" not in self._instances:
            self._instances["document_processor"] = None
        return self._instances["document_processor"]

    async def close_connections(self):
        """Fecha todas as conexões"""
        if "redis_client" in self._instances:
            await self._instances["redis_client"].close()

        await db_connection.close()


container = Container()


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


def get_threshold_service() -> ThresholdService:
    """Dependency para ThresholdService"""
    return ThresholdService(settings=settings)


async def get_search_service(
    vector_repo: PostgresVectorRepository = Depends(get_postgres_vector_repository),
    threshold_service: ThresholdService = Depends(get_threshold_service),
) -> SearchService:
    """Dependency para SearchService com PostgreSQL"""
    return SearchService(
        vector_repository=vector_repo, threshold_service=threshold_service
    )


async def get_chat_use_case(
    chat_service: ChatService = Depends(get_chat_service),
    search_service: SearchService = Depends(get_search_service),
    llm_service: LLMServiceInterface = Depends(get_llm_service),
) -> ChatWithDocumentsUseCase:
    """Dependency para ChatWithDocumentsUseCase com PostgreSQL (para FastAPI)"""
    return ChatWithDocumentsUseCase(
        chat_service=chat_service,
        search_service=search_service,
        llm_service=llm_service,
    )


async def create_chat_use_case() -> ChatWithDocumentsUseCase:
    """Cria ChatWithDocumentsUseCase sem Depends (para chamada direta)"""
    chat_service = container.get_chat_service()
    llm_service = container.get_llm_service()

    from infrastructure.database.connection import get_db_session

    async for session in get_db_session():
        vector_repo = PostgresVectorRepository(session)
        search_service = SearchService(vector_repository=vector_repo)

        return ChatWithDocumentsUseCase(
            chat_service=chat_service,
            search_service=search_service,
            llm_service=llm_service,
        )


async def get_postgres_file_upload_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresFileUploadRepository:
    """Dependency para PostgresFileUploadRepository"""
    return PostgresFileUploadRepository(session)


async def get_postgres_document_processing_job_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresDocumentProcessingJobRepository:
    """Dependency para PostgresDocumentProcessingJobRepository"""
    return PostgresDocumentProcessingJobRepository(session)


def get_s3_service() -> S3Service:
    """Dependency para S3Service"""
    return container.get_s3_service()


def get_text_chunker() -> TextChunker:
    """Dependency para TextChunker"""
    return container.get_text_chunker()


async def get_document_service(
    document_repo: PostgresDocumentRepository = Depends(
        get_postgres_document_repository
    ),
    document_chunk_repo: PostgresDocumentChunkRepository = Depends(
        get_postgres_document_chunk_repository
    ),
) -> DocumentService:
    """Dependency para DocumentService"""
    return DocumentService(
        document_repository=document_repo,
        document_chunk_repository=document_chunk_repo,
    )


async def get_document_processor(
    document_service: DocumentService = Depends(get_document_service),
    vector_repo: PostgresVectorRepository = Depends(get_postgres_vector_repository),
    text_chunker: TextChunker = Depends(get_text_chunker),
    openai_client: OpenAIClient = Depends(lambda: container.get_openai_client()),
    s3_service: S3Service = Depends(get_s3_service),
    document_repo: PostgresDocumentRepository = Depends(
        get_postgres_document_repository
    ),
) -> DocumentProcessor:
    """Dependency para DocumentProcessor"""
    return DocumentProcessor(
        document_service=document_service,
        vector_repository=vector_repo,
        text_chunker=text_chunker,
        openai_client=openai_client,
        s3_service=s3_service,
        document_repository=document_repo,
    )


async def get_create_presigned_upload_use_case(
    s3_service: S3Service = Depends(get_s3_service),
    file_upload_repo: PostgresFileUploadRepository = Depends(
        get_postgres_file_upload_repository
    ),
) -> CreatePresignedUploadUseCase:
    """Dependency para CreatePresignedUploadUseCase"""
    return CreatePresignedUploadUseCase(
        s3_service=s3_service,
        file_upload_repository=file_upload_repo,
    )


async def get_process_document_use_case(
    file_upload_repo: PostgresFileUploadRepository = Depends(
        get_postgres_file_upload_repository
    ),
    job_repo: PostgresDocumentProcessingJobRepository = Depends(
        get_postgres_document_processing_job_repository
    ),
) -> ProcessUploadedDocumentUseCase:
    """Dependency para ProcessUploadedDocumentUseCase"""
    return ProcessUploadedDocumentUseCase(
        file_upload_repository=file_upload_repo,
        job_repository=job_repo,
    )


async def get_document_status_use_case(
    job_repo: PostgresDocumentProcessingJobRepository = Depends(
        get_postgres_document_processing_job_repository
    ),
) -> GetDocumentStatusUseCase:
    """Dependency para GetDocumentStatusUseCase"""
    return GetDocumentStatusUseCase(job_repository=job_repo)


async def get_job_status_use_case(
    job_repo: PostgresDocumentProcessingJobRepository = Depends(
        get_postgres_document_processing_job_repository
    ),
) -> GetJobStatusUseCase:
    """Dependency para GetJobStatusUseCase"""
    return GetJobStatusUseCase(job_repository=job_repo)
