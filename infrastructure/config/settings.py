import os
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

from infrastructure.config.database_settings import database_settings


class Settings(BaseSettings):

    app_name: str = "Intelligent Document Search API"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")

    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL"
    )
    openai_max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")

    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")

    @property
    def database_url(self) -> str:
        return database_settings.database_url

    @property
    def sync_database_url(self) -> str:
        return database_settings.sync_database_url

    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    use_contextual_retrieval: bool = Field(default=True, env="USE_CONTEXTUAL_RETRIEVAL")

    default_search_results: int = Field(default=5, env="DEFAULT_SEARCH_RESULTS")

    similarity_threshold_default: float = Field(
        default=0.45, env="SIMILARITY_THRESHOLD_DEFAULT"
    )
    similarity_threshold_specific: float = Field(
        default=0.5, env="SIMILARITY_THRESHOLD_SPECIFIC"
    )
    similarity_threshold_general: float = Field(
        default=0.35, env="SIMILARITY_THRESHOLD_GENERAL"
    )
    similarity_threshold_technical: float = Field(
        default=0.6, env="SIMILARITY_THRESHOLD_TECHNICAL"
    )

    similarity_threshold: float = Field(default=0.45, env="SIMILARITY_THRESHOLD")

    max_messages_per_session: int = Field(default=100, env="MAX_MESSAGES_PER_SESSION")
    max_daily_messages: int = Field(default=50, env="MAX_DAILY_MESSAGES")
    session_ttl_hours: int = Field(default=24, env="SESSION_TTL_HOURS")

    documents_directory: str = Field(
        default="./storage/documents", env="DOCUMENTS_DIRECTORY"
    )
    logs_directory: str = Field(default="./storage/logs", env="LOGS_DIRECTORY")

    aws_access_key: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY")
    aws_secret_key: Optional[str] = Field(default=None, env="AWS_SECRET_KEY")
    s3_bucket: str = Field(default="documents", env="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", env="S3_REGION")
    s3_endpoint_url: Optional[str] = Field(default=None, env="S3_ENDPOINT_URL")
    s3_public_endpoint_url: Optional[str] = Field(
        default=None, env="S3_PUBLIC_ENDPOINT_URL"
    )

    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: list = Field(default=["*"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")

    # JWT Authentication
    jwt_secret: str = Field(env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiry_days: int = Field(default=3, env="JWT_EXPIRY_DAYS")

    # Google OAuth2
    google_client_id: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(
        default=None, env="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback", env="GOOGLE_REDIRECT_URI"
    )

    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    sqlalchemy_log_level: str = Field(default="WARNING", env="SQLALCHEMY_LOG_LEVEL")
    external_libs_log_level: str = Field(
        default="WARNING", env="EXTERNAL_LIBS_LOG_LEVEL"
    )

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG environment variable more flexibly"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return False

    def get_redis_url(self) -> str:
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


settings = Settings()
