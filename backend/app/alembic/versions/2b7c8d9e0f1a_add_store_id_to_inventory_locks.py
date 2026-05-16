"""add_store_id_to_inventory_locks

Revision ID: 2b7c8d9e0f1a
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-16 20:40:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "2b7c8d9e0f1a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE inventory_locks
        ADD COLUMN IF NOT EXISTS store_id INTEGER
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'inventory_locks_store_id_fkey'
            ) THEN
                ALTER TABLE inventory_locks
                ADD CONSTRAINT inventory_locks_store_id_fkey
                FOREIGN KEY (store_id) REFERENCES stores(store_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_inventory_locks_store_id
        ON inventory_locks (store_id)
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_inventory_locks_store_id")
    op.execute(
        """
        ALTER TABLE inventory_locks
        DROP CONSTRAINT IF EXISTS inventory_locks_store_id_fkey
        """
    )
    op.execute(
        """
        ALTER TABLE inventory_locks
        DROP COLUMN IF EXISTS store_id
        """
    )
