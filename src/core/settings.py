from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_telegram_ids: tuple[int, ...] = Field(default=(), alias="ADMIN_TELEGRAM_IDS")
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_env: str = Field(default="dev", alias="APP_ENV")
    price_city: str = Field(default="moscow", alias="PRICE_CITY")
    sync_cron: str = Field(default="0 10 * * 1", alias="SYNC_CRON")

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_admin_telegram_ids(cls, value: object) -> tuple[int, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)
        raise TypeError("Unsupported ADMIN_TELEGRAM_IDS format")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
