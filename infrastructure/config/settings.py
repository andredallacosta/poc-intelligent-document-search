import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from infrastructure.config.database_settings import database_settings


class Settings(BaseSettings):
    
    # Application
    app_name: str = "Intelligent Document Search API"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # OpenAI
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # ChromaDB (TEMPORÁRIO - será removido após migração)
    chroma_persist_directory: str = Field(default="./storage/vector_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="documents", env="CHROMA_COLLECTION_NAME")
    
    # PostgreSQL (via database_settings)
    @property
    def database_url(self) -> str:
        return database_settings.database_url
    
    @property
    def sync_database_url(self) -> str:
        return database_settings.sync_database_url
    
    # Document Processing
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    use_contextual_retrieval: bool = Field(default=True, env="USE_CONTEXTUAL_RETRIEVAL")
    
    # Search
    default_search_results: int = Field(default=5, env="DEFAULT_SEARCH_RESULTS")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Rate Limiting
    max_messages_per_session: int = Field(default=100, env="MAX_MESSAGES_PER_SESSION")
    max_daily_messages: int = Field(default=50, env="MAX_DAILY_MESSAGES")
    session_ttl_hours: int = Field(default=24, env="SESSION_TTL_HOURS")
    
    # Storage
    documents_directory: str = Field(default="./storage/documents", env="DOCUMENTS_DIRECTORY")
    logs_directory: str = Field(default="./storage/logs", env="LOGS_DIRECTORY")
    
    # Security
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: list = Field(default=["*"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG environment variable more flexibly"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return False
    
    def get_redis_url(self) -> str:
        # Use REDIS_URL if provided, otherwise construct from components
        if self.redis_url:
            return self.redis_url
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def session_ttl_seconds(self) -> int:
        return self.session_ttl_hours * 3600
    
    def create_directories(self):
        os.makedirs(self.documents_directory, exist_ok=True)
        os.makedirs(self.logs_directory, exist_ok=True)
        os.makedirs(self.chroma_persist_directory, exist_ok=True)


# Global settings instance
settings = Settings()
