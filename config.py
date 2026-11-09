from __future__ import annotations

import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    admin_ids: list[int] = []
    default_language: str = "ru"
    questions_per_test: int = 20
    answer_unlock_price: int = 50
    donation_min_stars: int = 1
    donation_max_stars: int = 10000
    log_level: str = "INFO"
    health_host: str = "0.0.0.0"
    health_port: int = 8080
    db_path: str = "data/bot.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value) -> list[int]:
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [int(x) for x in value]
        text = str(value).strip()
        if text.startswith("["):
            try:
                return [int(x) for x in json.loads(text)]
            except Exception:
                pass
        return [int(x.strip()) for x in text.split(",") if x.strip()]


settings = Settings()
