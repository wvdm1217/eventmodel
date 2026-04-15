from pydantic_settings import BaseSettings, SettingsConfigDict


class EventModelSettings(BaseSettings):
    nats_url: str = "nats://localhost:4222"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = EventModelSettings()
