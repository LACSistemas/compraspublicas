from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_TIMEOUT_MS: int = 90000
    DATABASE_URL: str = "sqlite:///./data/app.db"
    MAX_PROCESSOS: int = 10
    DOWNLOADS_DIR: str = "downloads"
    CORS_ORIGINS: str = "http://localhost:3000"
    FONTE_DADOS: str = "portal"
    GEMINI_MODEL_GERACAO: str = ""
    GERACOES_DIR: str = "geracoes"
    FONTES_VERDADE_DIR: str = "fontes_verdade"
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OWNER_EMAIL: str = ""
    OWNER_PASSWORD: str = ""
    INVESTIGACAO_HABILITADA: bool = False
    UPLOADS_DIR: str = "uploads"
    MAX_UPLOAD_BYTES: int = 20_000_000
    TOKEN_BUDGET_CONTRATACAO: int = 500_000

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
