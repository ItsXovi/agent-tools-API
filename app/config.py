from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PDF Toolkit API"
    app_version: str = "0.2.0"
    debug: bool = False
    require_api_key: bool = False
    admin_secret: str = ""
    database_path: str = "data/agent_tools.db"
    max_pdf_bytes: int = 10_485_760  # 10 MB


settings = Settings()
