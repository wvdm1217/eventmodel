from pydantic_settings import BaseSettings, SettingsConfigDict


class EventModelSettings(BaseSettings):
    nats_url: str = "nats://localhost:4222"
    worker_count: int = 5

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = EventModelSettings()
