from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    claude_model_primary: str = "claude-sonnet-4-6"
    claude_model_light: str = "claude-haiku-4-5-20251001"

    redis_url: str = "redis://localhost:6379/0"

    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    images_dir: str = "uploads/images"

    max_file_size_mb: int = 50
    translation_batch_size: int = 5   # 한 번에 번역할 블록 수
    max_context_blocks: int = 3        # 앞뒤 맥락 블록 수

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
