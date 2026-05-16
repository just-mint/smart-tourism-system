"""add_price_override_to_inventory

Revision ID: 3c8d9e0f1a2b
Revises: 2b7c8d9e0f1a
Create Date: 2026-05-16 20:47:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "3c8d9e0f1a2b"
down_revision = "2b7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE inventory
        ADD COLUMN IF NOT EXISTS price_override INTEGER
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE inventory
        DROP COLUMN IF EXISTS price_override
        """
    )
