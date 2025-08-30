import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "POC Intelligent Document Search API"
    version: str = "1.0.0"
    environment: str = "development"
    
    redis_url: str = "redis://localhost:6379"
    
    openai_api_key: Optional[str] = None
    
    session_ttl_hours: int = 24
    max_messages_per_session: int = 10
    max_tokens_per_request: int = 8000
    max_requests_per_session_day: int = 50
    
    chroma_db_path: str = "./data/chroma_db"
    
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
