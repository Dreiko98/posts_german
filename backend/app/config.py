from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://studio:missing@db/studio"
    master_key: str = ""
    app_origin: str = "http://localhost:8080"
    cookie_secure: bool = False
    data_dir: Path = Path("/data")
    app_name: str = "Germán Content Studio"
    session_hours: int = 12
    linkedin_version: str = "202609"
    request_timeout: int = 90


settings = Settings()
