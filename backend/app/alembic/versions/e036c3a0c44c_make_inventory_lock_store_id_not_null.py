"""make inventory lock store_id not null

Revision ID: e036c3a0c44c
Revises: 873624317ede
Create Date: 2026-05-21 10:23:20.618890

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "e036c3a0c44c"
down_revision = "873624317ede"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM inventory_locks WHERE store_id IS NULL")
    op.execute("UPDATE inventory SET locked_stock = 0 WHERE locked_stock IS NULL")

    op.execute("ALTER TABLE inventory ALTER COLUMN store_id SET NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN product_id SET NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN locked_stock SET DEFAULT 0")
    op.execute("ALTER TABLE inventory ALTER COLUMN locked_stock SET NOT NULL")
    op.execute("ALTER TABLE inventory_locks ALTER COLUMN store_id SET NOT NULL")

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'inventory'
                  AND constraint_name = 'inventory_store_id_product_id_key'
            ) THEN
                ALTER TABLE inventory
                DROP CONSTRAINT inventory_store_id_product_id_key;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'inventory'
                  AND constraint_name = 'uq_inventory_store_product'
            ) THEN
                ALTER TABLE inventory
                ADD CONSTRAINT uq_inventory_store_product UNIQUE (store_id, product_id);
            END IF;
        END $$;
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_inventory_id "
        "ON inventory(inventory_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_locks_user_id "
        "ON inventory_locks(user_id)"
    )


def downgrade():
    op.execute("ALTER TABLE inventory_locks ALTER COLUMN store_id DROP NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN locked_stock DROP NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN product_id DROP NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN store_id DROP NOT NULL")
