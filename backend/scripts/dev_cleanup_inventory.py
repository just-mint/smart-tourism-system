import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

CONFIRM_FLAG = "--confirm-dev-truncate"


def _load_settings():
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.append(str(backend_root))

    from app.core.config import settings

    return settings


def cleanup_inventory() -> None:
    settings = _load_settings()
    if settings.ENVIRONMENT != "local":
        raise RuntimeError(
            "Refusing to truncate data outside local environment. "
            f"Current ENVIRONMENT={settings.ENVIRONMENT!r}."
        )

    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    with engine.begin() as conn:
        logger.warning("Truncating inventory, stores, and products tables.")
        conn.execute(text("TRUNCATE TABLE inventory, stores, products CASCADE;"))
        logger.info("Development inventory cleanup complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Development-only cleanup for O2O inventory seed data. "
            "This runs TRUNCATE ... CASCADE and must never be used in production."
        )
    )
    parser.add_argument(
        CONFIRM_FLAG,
        action="store_true",
        help="Required confirmation that destructive local cleanup is intended.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    if not getattr(args, CONFIRM_FLAG.removeprefix("--").replace("-", "_")):
        logger.error("Missing required confirmation flag: %s", CONFIRM_FLAG)
        return 2

    try:
        cleanup_inventory()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
