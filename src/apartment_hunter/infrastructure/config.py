from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "apartment_hunter.db"
    log_level: str = "INFO"

    geocoding_user_agent: str = "listing-hunter/0.1.0"
    # Where the Carte des loyers files are kept once downloaded, one folder per vintage.
    rent_map_cache_dir: str = ".cache/carte-des-loyers"

    rate_limit_seconds: float = 1.5
    max_concurrent_crawlers: int = 5
    request_timeout_seconds: float = 30.0


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
