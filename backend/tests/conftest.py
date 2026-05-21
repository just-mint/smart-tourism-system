# ruff: noqa: E402

import re
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, delete

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env.test", override=True)

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Item, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def _ensure_test_database_exists() -> None:
    db_url = make_url(str(settings.SQLALCHEMY_DATABASE_URI))
    db_name = db_url.database
    if settings.ENVIRONMENT != "local":
        raise RuntimeError("Refusing to run tests against a non-local database.")
    if not db_name or not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
        raise RuntimeError(f"Unsafe test database name: {db_name!r}")

    maintenance_url = db_url.set(database="postgres")
    maintenance_engine = create_engine(
        maintenance_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        with maintenance_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        maintenance_engine.dispose()


def _run_test_migrations() -> None:
    alembic_cfg = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(REPO_ROOT / "backend" / "app" / "alembic"),
    )
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    _ensure_test_database_exists()
    _run_test_migrations()

    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(Item)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
