import secrets
import warnings
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

REPO_ROOT = Path(__file__).resolve().parents[3]


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use the repository-level .env regardless of the current working directory.
        env_file=REPO_ROOT / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 30 minutes for security hardening
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        raw_origins = (
            self.BACKEND_CORS_ORIGINS
            if isinstance(self.BACKEND_CORS_ORIGINS, list)
            else [self.BACKEND_CORS_ORIGINS]
        )
        return [str(origin).rstrip("/") for origin in raw_origins if origin] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    # Inventory: Thời gian giữ Soft-lock (giây). Mặc định 15 phút.
    INVENTORY_LOCK_TTL: int = 900

    # Infrastructure services
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"
    OPTIMIZATION_SERVICE_URL: str = "http://localhost:8001/api/v1/optimize"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"

    # Internal Secret: Dùng cho service-to-service auth (Celery → API, Cronjob → API)
    INTERNAL_SECRET_KEY: str = secrets.token_urlsafe(32)

    # Rate limiting for expensive O2O endpoints
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_LIMIT: int = 60
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = 60

    # Vision Upload: Kiểu file và dung lượng tối đa cho API /vision/scan
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_ROOT: str = "uploads"

    # Gemini AI
    GEMINI_API_KEY: str | None = None

    # Payment webhook guard. Production should set a stable HMAC secret.
    PAYMENT_PROVIDER: str = "vietqr_mock"
    PAYMENT_WEBHOOK_SECRET: str | None = None

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        if self.ENVIRONMENT == "production":
            raw_origins = (
                self.BACKEND_CORS_ORIGINS
                if isinstance(self.BACKEND_CORS_ORIGINS, list)
                else [self.BACKEND_CORS_ORIGINS]
            )
            origins = [str(origin) for origin in raw_origins]
            if "*" in origins:
                raise ValueError("BACKEND_CORS_ORIGINS must not contain '*' in production")
            if not self.PAYMENT_WEBHOOK_SECRET:
                raise ValueError("PAYMENT_WEBHOOK_SECRET is required in production")

        return self


settings = Settings()  # type: ignore
