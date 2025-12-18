from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Video Unique Service"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/video_unique"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Storage (S3)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "videos"
    S3_REGION_NAME: str = "us-east-1"

    class Config:
        env_file = ".env"

settings = Settings()
