from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database
    # Default to a local SQLite file for easier local development if Postgres isn't available.
    # Override with env var DATABASE_URL for production/Postgres usage.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/temporal_dev.db")
    
    # Application
    environment: str = "development"
    debug: bool = True
    secret_key: str = "your-secret-key-change-in-production"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # File Storage
    upload_dir: str = "data/uploads"
    processed_dir: str = "data/processed"
    cache_dir: str = "data/cache"
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
