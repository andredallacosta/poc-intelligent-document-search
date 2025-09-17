from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    # PostgreSQL Connection
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="intelligent_document_search", env="POSTGRES_DB")
    
    # Connection Pool Settings
    postgres_pool_size: int = Field(default=10, env="POSTGRES_POOL_SIZE")
    postgres_max_overflow: int = Field(default=20, env="POSTGRES_MAX_OVERFLOW")
    postgres_pool_timeout: int = Field(default=30, env="POSTGRES_POOL_TIMEOUT")
    postgres_pool_recycle: int = Field(default=3600, env="POSTGRES_POOL_RECYCLE")
    
    # SSL Settings
    postgres_ssl_mode: str = Field(default="prefer", env="POSTGRES_SSL_MODE")
    
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_ssl_mode}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """URL síncrona para Alembic migrations"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_ssl_mode}"
        )


# Global instance
database_settings = DatabaseSettings()
