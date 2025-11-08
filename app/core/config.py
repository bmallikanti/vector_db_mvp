from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    COHERE_API_KEY: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields (e.g., old Redis config)
    )


settings = Settings()
