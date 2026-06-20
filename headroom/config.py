from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    redis_url: str = "redis://localhost:6379/0"
    upstream_base_url: str = "https://api.openai.com"
    log_level: str = "info"
    provider: str = ""
    dry_run: bool = False

    model_config = {"env_prefix": "HEADROOM_"}


settings = Settings()
