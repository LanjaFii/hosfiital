from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://hosfiital:hosfiital_dev_password@localhost:5433/hosfiital"
    SECRET_KEY: str = "changeme"
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
