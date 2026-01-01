from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Security
    api_key: str = "change-me"

    # WebDAV
    nextcloud_username: str
    nextcloud_password: str
    webdav_url: str

    # aria2 Configuration
    aria2_rpc_url: str = "http://localhost:6800/jsonrpc"
    aria2_rpc_secret: str = "change-me-aria2-secret"
    aria2_max_connections: int = 16
    aria2_split: int = 16
    aria2_max_concurrent_downloads: int = 5
    aria2_enable_fallback: bool = True

    # System
    max_file_size_gb: int = 5
    celery_worker_concurrency: int = 2
    download_timeout: int = 3600
    max_retries: int = 3

    # Paths
    storage_path: str = "/app/storage/temp"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
