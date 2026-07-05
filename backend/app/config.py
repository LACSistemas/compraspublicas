from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    DATABASE_URL: str = "sqlite:///./data/app.db"
    MAX_PROCESSOS: int = 10
    DOWNLOADS_DIR: str = "downloads"
    CORS_ORIGINS: str = "http://localhost:3000"
    FONTE_DADOS: str = "portal"
    GEMINI_MODEL_GERACAO: str = ""
    GERACOES_DIR: str = "geracoes"
    FONTES_VERDADE_DIR: str = "fontes_verdade"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
