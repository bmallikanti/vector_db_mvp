from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    COHERE_API_KEY: str | None = None
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False  # Set to True to use Redis instead of in-memory
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
