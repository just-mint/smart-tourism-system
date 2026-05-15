"""Add store id to inventory locks

Revision ID: 8d41c9b2a7e5
Revises: 6f2c1e9b8a30
Create Date: 2026-05-15 21:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "8d41c9b2a7e5"
down_revision = "6f2c1e9b8a30"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("inventory_locks")}

    if "store_id" not in columns:
        op.add_column("inventory_locks", sa.Column("store_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_inventory_locks_store_id_stores",
            "inventory_locks",
            "stores",
            ["store_id"],
            ["store_id"],
        )
        op.create_index("ix_inventory_locks_store_id", "inventory_locks", ["store_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("inventory_locks")}

    if "store_id" in columns:
        op.drop_index("ix_inventory_locks_store_id", table_name="inventory_locks")
        op.drop_constraint("fk_inventory_locks_store_id_stores", "inventory_locks", type_="foreignkey")
        op.drop_column("inventory_locks", "store_id")
