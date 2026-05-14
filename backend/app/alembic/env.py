import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
fileConfig(config.config_file_name)

from app.models import SQLModel  # noqa — registers User, Item into SQLModel.metadata
from app.core.config import settings  # noqa
from app.db.session import Base  # noqa — Base for domain models

# ── Import all domain models so they register into Base.metadata ──
from app.domains.culture import model as culture_model  # noqa
from app.domains.inventory import model as inventory_model  # noqa
from app.domains.vision import model as vision_model  # noqa
# Note: agent & spatial domains use models from culture/inventory, no separate model.py

# Alembic hỗ trợ list metadata — đơn giản và chính xác nhất
target_metadata = [SQLModel.metadata, Base.metadata]

# ── Tập hợp TẤT CẢ tên table của app (từ cả 2 metadata) ──
_APP_TABLES: set[str] = set()
for _meta in target_metadata:
    _APP_TABLES.update(_meta.tables.keys())


def include_object(object, name, type_, reflected, compare_to):
    """
    Chỉ cho Alembic theo dõi các table của app.
    Bỏ qua toàn bộ bảng PostGIS Tiger geocoder và extension tables
    (spatial_ref_sys, faces, edges, topology, loader_*, zip_*, v.v.)
    """
    if type_ == "table":
        return name in _APP_TABLES
    return True


def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

