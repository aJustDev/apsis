import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "apsis"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "local"

    # CORS: origenes permitidos para fetch cross-origin (coma-separados).
    # Vacio = sin CORS (default local); en deploy = el dominio del front estatico.
    CORS_ORIGINS: str = ""

    # Database. DATABASE_URL is derived from the parts unless set explicitly.
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "apsis"
    DB_PASSWORD: str = "apsis"  # noqa: S105 - local dev default
    DB_NAME: str = "apsis_dev"
    DATABASE_URL: str = ""

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Scheduled jobs (core/jobs).
    JOB_POLL_INTERVAL_SECONDS: float = 5.0
    JOB_LEASE_SECONDS: int = 120
    JOB_HANDLER_TIMEOUT_SECONDS: int = 55

    # Transactional outbox (core/events).
    OUTBOX_POLL_INTERVAL_SECONDS: float = 5.0
    OUTBOX_HANDLER_TIMEOUT_SECONDS: int = 30
    OUTBOX_MAX_RETRIES: int = 8

    # CelesTrak TLE source. Cache window matches their 2h refresh; fetching the
    # same group more often returns HTTP 403, so the ingest job respects it.
    CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"
    CELESTRAK_GROUP: str = "active"
    CELESTRAK_TIMEOUT_SECONDS: float = 30.0

    # Pass prediction: ventana hacia delante que recalcula el outbox.
    PASS_PREDICTION_HORIZON_HOURS: int = 48

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('ENVIRONMENT', 'local')}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    @model_validator(mode="after")
    def validate_lease_invariant(self) -> "Settings":
        # El lease debe cubrir al menos dos timeouts de handler para que un job
        # lento no sea reclamado como zombi mientras sigue corriendo.
        if self.JOB_LEASE_SECONDS < 2 * self.JOB_HANDLER_TIMEOUT_SECONDS:
            raise ValueError(
                "JOB_LEASE_SECONDS must be >= 2 * JOB_HANDLER_TIMEOUT_SECONDS"
            )
        return self


settings = Settings()
