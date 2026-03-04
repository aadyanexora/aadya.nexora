try:
    from pydantic_settings import BaseSettings
except Exception:
    from pydantic import BaseSettings

from pathlib import Path


class Settings(BaseSettings):
    # database URL must be supplied in production; SQLite support has been removed.
    DATABASE_URL: str
    SECRET_KEY: str
    FAISS_DIR: str = "./faiss_data"
    EMBEDDING_DIM: int = 384
    PROJECT_NAME: str = "Aadya - Nexora AI"
    GROQ_API_KEY: str  # key for Groq chat provider
    # allowed CORS origins (comma-separated or list in env)
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # default administrator credentials (can be overridden via env or .env)
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"

    # test user credentials (non-admin)
    DEFAULT_USER_EMAIL: str = "user@example.com"
    DEFAULT_USER_PASSWORD: str = "password"

    # cost per token for each model, used to estimate billing
    MODEL_PRICING: dict = {"llama-3.1-8b-instant": 0.0001}

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
