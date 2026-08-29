"""
Application configuration.

All secrets/config come from environment variables (.env in dev, real env
vars in production). Nothing sensitive is hardcoded or committed.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "MedLink API"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = False

    # --- Database ---
    # In development, falls back to local SQLite if DATABASE_URL isn't set.
    # In production, DATABASE_URL MUST be a postgresql:// URL.
    DATABASE_URL: str = "sqlite:///./medlink.db"

    # --- Auth / JWT ---
    # No default secret — the app refuses to start in production without one.
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    # Comma-separated list of allowed origins. No wildcard in production.
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Rate limiting ---
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def ENV(self) -> str:
        return self.APP_ENV

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()

# Hard safety check: never allow the app to boot in production with an
# insecure/default secret or a non-Postgres database.
if settings.is_production:
    if len(settings.SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production.")
    if not settings.DATABASE_URL.startswith("postgresql"):
        raise RuntimeError("Production must use PostgreSQL, not SQLite.")
    if "*" in settings.CORS_ORIGINS:
        raise RuntimeError("Wildcard CORS origin is not allowed in production.")
