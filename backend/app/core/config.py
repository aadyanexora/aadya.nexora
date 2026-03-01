try:
    from pydantic_settings import BaseSettings
except Exception:
    from pydantic import BaseSettings

from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    FAISS_DIR: str = "./faiss_data"
    EMBEDDING_DIM: int = 384
    PROJECT_NAME: str = "Aadya - Nexora AI"
    GROQ_API_KEY: str  # key for Groq chat provider

    # default administrator credentials (can be overridden via env or .env)
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"


settings = Settings()
