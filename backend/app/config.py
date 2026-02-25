from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "StockAI"
    env: str = "dev"
    api_port: int = 8000

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://stockai-project.vercel.app/"

    scheduler_enabled: bool = True
    scheduler_cron: str = "30 22 * * 1-5"
    
    # Universe settings
    use_sp500_universe: bool = False
    refresh_batch_size: int = 50
    refresh_delay_seconds: float = 1.0


settings = Settings()
