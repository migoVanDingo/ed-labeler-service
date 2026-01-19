from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "example-core-service"
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    REDIS_URL: str = "redis://localhost:6379"
    GCS_BUCKET: str = ""
    LABEL_STUDIO_BASE_URL: str = ""
    LABEL_STUDIO_API_KEY: str = ""
    LABEL_STUDIO_WEBHOOK_SECRET: str = ""
    LABEL_STUDIO_MEDIA_TOKEN: str = ""
    LABEL_STUDIO_LABEL_CONFIG: str = ""
    PUBLIC_BASE_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
