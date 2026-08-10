"""Cloud-Konfiguration / Cloud configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DE: Cloud-Werte aus `.env`. EN: Cloud values loaded from `.env`."""
    cloud_host: str = "127.0.0.1"
    cloud_port: int = 8090
    cloud_db: str = "./data/cloud.db"
    cloud_api_token: str = ""
    cloud_allow_commands: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
