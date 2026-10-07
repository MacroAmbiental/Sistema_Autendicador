from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Aplicação
    app_name: str = "Autenticador Macroambiental"
    app_env: str = "development"
    debug: bool = False

    # Banco de dados
    database_url: str = ""

    # CORS
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://sistema-de-equipamentos.onrender.com",
        "https://sistema-autendicador.onrender.com"
    )

    # Firebase
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()