from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://vocabestie:vocabestie@localhost:5433/vocabestie"

    class Config:
        env_file = ".env"


settings = Settings()
