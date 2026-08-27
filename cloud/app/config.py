"""Cloud-Konfiguration / Cloud configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cloud values loaded from `.env` or the process environment."""

    cloud_host: str = "127.0.0.1"
    cloud_port: int = 8090
    cloud_db: str = "./data/cloud.db"
    cloud_api_token: str = ""
    cloud_admin_token: str = ""
    cloud_diagnostic_read_token: str = ""
    cloud_allow_commands: bool = False
    cloud_closed_test_mode: bool = False
    cloud_closed_test_site: str = "closed-test"
    cloud_telemetry_retention_rows: int = 50_000
    cloud_diagnostic_event_retention_rows: int = 10_000

    # Server administration defaults. These values are deliberately stored in
    # the common Cloud Core and are therefore shared by Plesk and standalone UI.
    cloud_admin_mode: str = "standalone"  # standalone | plesk | both
    cloud_max_devices: int = 1000
    cloud_heartbeat_seconds: int = 30
    cloud_offline_after_seconds: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
