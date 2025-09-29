from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    CEREBRAS_API_KEY: str
    GITHUB_TOKEN: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
