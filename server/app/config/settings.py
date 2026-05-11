from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="PhotoAI", alias="PHOTOAI_APP_NAME")
    env: str = Field(default="development", alias="PHOTOAI_ENV")
    base_url: str = Field(default="http://localhost:8080", alias="PHOTOAI_BASE_URL")
    jwt_secret: str = Field(default="change_this_secret_to_a_long_random_value", alias="PHOTOAI_JWT_SECRET")
    access_token_expire_minutes: int = Field(default=30, alias="PHOTOAI_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, alias="PHOTOAI_REFRESH_TOKEN_EXPIRE_DAYS")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="photoai", alias="POSTGRES_DB")
    postgres_user: str = Field(default="photoai", alias="POSTGRES_USER")
    postgres_password: str = Field(default="photoai_password", alias="POSTGRES_PASSWORD")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    storage_root: Path = Field(default=Path("./data/photoai"), alias="PHOTOAI_STORAGE_ROOT")
    originals_dir: Path = Field(default=Path("./data/photoai/originals"), alias="PHOTOAI_ORIGINALS_DIR")
    thumbnails_dir: Path = Field(default=Path("./data/photoai/thumbnails"), alias="PHOTOAI_THUMBNAILS_DIR")
    previews_dir: Path = Field(default=Path("./data/photoai/previews"), alias="PHOTOAI_PREVIEWS_DIR")
    cache_dir: Path = Field(default=Path("./data/photoai/cache"), alias="PHOTOAI_CACHE_DIR")

    max_upload_size_mb: int = Field(default=10240, alias="PHOTOAI_MAX_UPLOAD_SIZE_MB")
    chunk_size_mb: int = Field(default=8, alias="PHOTOAI_CHUNK_SIZE_MB")

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def default_chunk_size(self) -> int:
        return self.chunk_size_mb * 1024 * 1024

    @computed_field
    @property
    def max_upload_size(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
