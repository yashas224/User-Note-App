from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./notes.db"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 12
    # Where share links point: the Streamlit app, which renders ?share=<token>.
    PUBLIC_BASE_URL: str = "http://localhost:8501"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def _algorithm_allowed(cls, v: str) -> str:
        if v not in ALLOWED_JWT_ALGORITHMS:
            raise ValueError(f"JWT_ALGORITHM must be one of {ALLOWED_JWT_ALGORITHMS}")
        return v


settings = Settings()
