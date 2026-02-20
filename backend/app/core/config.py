from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Novel Creator API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/novel.db"

    # LLM
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4"
    LLM_MAX_RETRIES: int = 3

    # Context Pack budgets (tokens)
    CTX_SYSTEM_RESERVED: int = 1024
    CTX_SYSTEM_MAX: int = 2048
    CTX_LONGTERM_RESERVED: int = 2048
    CTX_LONGTERM_MAX: int = 4096
    CTX_STRUCTURED_MAX: int = 6144

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
