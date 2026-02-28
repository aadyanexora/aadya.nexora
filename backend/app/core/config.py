try:
    from pydantic_settings import BaseSettings
except Exception:
    from pydantic import BaseSettings

from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    SECRET_KEY: str
    FAISS_DIR: str = "./faiss_data"
    EMBEDDING_DIM: int = 1536
    PROJECT_NAME: str = "Aadya - Nexora AI"
    GROQ_API_KEY: str  # key for Groq chat provider

    class Config:
        env_file = ".env"


settings = Settings()
