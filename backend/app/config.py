from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    gemini_model_primary: str = "gemini-1.5-flash"
    gemini_model_light: str = "gemini-1.5-flash"

    redis_url: str = "redis://localhost:6379/0"

    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    images_dir: str = "uploads/images"

    max_file_size_mb: int = 50
    translation_batch_size: int = 5
    max_context_blocks: int = 3

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
