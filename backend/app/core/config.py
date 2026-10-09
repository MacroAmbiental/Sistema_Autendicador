from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Autenticador Macroambiental"
    app_env: str = "development"
    debug: bool = False
    database_url: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    # firebase em producao; local SOMENTE quando explicitamente ativado em dev/teste.
    auth_storage_mode: str = "firebase"
    auth_local_dir: str = "./local_auth_data"
    integration_api_key: str = ""
    admin_api_key: str = ""
    verification_base_url: str = "http://localhost:5173"
    max_pdf_bytes: int = 12_000_000
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
