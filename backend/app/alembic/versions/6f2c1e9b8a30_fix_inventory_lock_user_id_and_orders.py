"""Fix inventory lock user id and create orders table

Revision ID: 6f2c1e9b8a30
Revises: 4f7b9d2c8a1e
Create Date: 2026-05-15 20:20:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "6f2c1e9b8a30"
down_revision = "4f7b9d2c8a1e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "inventory_locks" in inspector.get_table_names():
        user_id_col = next(
            (
                col
                for col in inspector.get_columns("inventory_locks")
                if col["name"] == "user_id"
            ),
            None,
        )
        if user_id_col and not isinstance(user_id_col["type"], postgresql.UUID):
            op.execute("DELETE FROM inventory_locks WHERE status != 'soft_locked'")
            op.execute("DELETE FROM inventory_locks")
            op.alter_column(
                "inventory_locks",
                "user_id",
                existing_type=sa.Integer(),
                type_=postgresql.UUID(as_uuid=True),
                postgresql_using="NULL::uuid",
                nullable=False,
            )

    if "orders" not in inspector.get_table_names():
        op.create_table(
            "orders",
            sa.Column("order_id", sa.Integer(), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("total_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("address", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING_SHIP"),
            sa.Column("order_code", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
            sa.ForeignKeyConstraint(["store_id"], ["stores.store_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        )
        op.create_index("ix_orders_order_id", "orders", ["order_id"])
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_order_code", "orders", ["order_code"], unique=True)


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "orders" in inspector.get_table_names():
        op.drop_index("ix_orders_order_code", table_name="orders")
        op.drop_index("ix_orders_user_id", table_name="orders")
        op.drop_index("ix_orders_order_id", table_name="orders")
        op.drop_table("orders")

    if "inventory_locks" in inspector.get_table_names():
        op.execute("DELETE FROM inventory_locks")
        op.alter_column(
            "inventory_locks",
            "user_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.Integer(),
            postgresql_using="0",
            nullable=False,
        )
