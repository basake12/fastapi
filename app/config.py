# app/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database — REQUIRED from environment
    database_username: str = os.getenv("DATABASE_USERNAME")
    database_password: str = os.getenv("DATABASE_PASSWORD")
    database_host: str = os.getenv("DATABASE_HOST")
    database_port: str = os.getenv("DATABASE_PORT", "5432")
    database_name: str = os.getenv("DATABASE_NAME")

    # JWT
    secret_key: str = os.getenv("SECRET_KEY")

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Optional
    database_url: Optional[str] = os.getenv("DATABASE_URL")  # Render/Supabase
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    env: str = os.getenv("ENV", "production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    @property
    def DATABASE_URL(self) -> str:
        """Build full PostgreSQL URL with psycopg2 driver."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+psycopg2://", 1)
            return url

        return (
            f"postgresql+psycopg2://{self.database_username}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Return Redis URL (with redis:// scheme)."""
        return self.redis_url

    class Config:
        env_file = ".env"  # Local dev only
        env_file_encoding = "utf-8"
        extra = "allow"
        case_sensitive = False


# Global settings instance
settings = Settings()