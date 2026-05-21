"""add review moderation fields

Revision ID: 5b0f7a8c2d91
Revises: e036c3a0c44c
Create Date: 2026-05-21 11:05:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "5b0f7a8c2d91"
down_revision = "e036c3a0c44c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS user_id uuid")
    op.execute(
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS "
        "moderation_status varchar(30) NOT NULL DEFAULT 'visible'"
    )
    op.execute(
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS "
        "report_count integer NOT NULL DEFAULT 0"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_reviews_user_id ON reviews(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_reviews_moderation_status "
        "ON reviews(moderation_status)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_reviews_moderation_status")
    op.execute("DROP INDEX IF EXISTS ix_reviews_user_id")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS report_count")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS moderation_status")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS user_id")
