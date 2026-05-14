"""Add review moderation fields

Revision ID: 4f7b9d2c8a1e
Revises: fe56fa70289e
Create Date: 2026-05-14 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "4f7b9d2c8a1e"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "reviews" not in inspector.get_table_names():
        op.create_table(
            "reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("place_id", sa.String(length=50), nullable=True),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("author_name", sa.String(length=100), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("time_posted", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("report_reason", sa.Text(), nullable=True),
            sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("moderated_by", sa.UUID(), nullable=True),
            sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("moderation_note", sa.Text(), nullable=True),
        )
        op.create_index("ix_reviews_place_id", "reviews", ["place_id"])
        op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
        op.create_index("ix_reviews_status", "reviews", ["status"])
        op.create_foreign_key(
            "reviews_user_id_fkey", "reviews", "user", ["user_id"], ["id"], ondelete="SET NULL"
        )
        op.create_foreign_key(
            "reviews_moderated_by_fkey",
            "reviews",
            "user",
            ["moderated_by"],
            ["id"],
            ondelete="SET NULL",
        )
        return

    op.add_column("reviews", sa.Column("user_id", sa.UUID(), nullable=True))
    op.add_column("reviews", sa.Column("status", sa.String(length=20), nullable=True))
    op.add_column("reviews", sa.Column("report_count", sa.Integer(), nullable=True))
    op.add_column("reviews", sa.Column("report_reason", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reviews", sa.Column("moderated_by", sa.UUID(), nullable=True))
    op.add_column("reviews", sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reviews", sa.Column("moderation_note", sa.Text(), nullable=True))
    op.execute("UPDATE reviews SET status = 'approved' WHERE status IS NULL")
    op.execute("UPDATE reviews SET report_count = 0 WHERE report_count IS NULL")
    op.alter_column("reviews", "status", nullable=False, server_default="pending")
    op.alter_column("reviews", "report_count", nullable=False, server_default="0")
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_reviews_status", "reviews", ["status"])
    op.create_foreign_key(
        "reviews_user_id_fkey", "reviews", "user", ["user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "reviews_moderated_by_fkey",
        "reviews",
        "user",
        ["moderated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("reviews_moderated_by_fkey", "reviews", type_="foreignkey")
    op.drop_constraint("reviews_user_id_fkey", "reviews", type_="foreignkey")
    op.drop_index("ix_reviews_status", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_column("reviews", "moderation_note")
    op.drop_column("reviews", "moderated_at")
    op.drop_column("reviews", "moderated_by")
    op.drop_column("reviews", "reported_at")
    op.drop_column("reviews", "report_reason")
    op.drop_column("reviews", "report_count")
    op.drop_column("reviews", "status")
    op.drop_column("reviews", "user_id")
