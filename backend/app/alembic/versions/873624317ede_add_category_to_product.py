"""Add category to Product

Revision ID: 873624317ede
Revises: 7f2b8d9c1a34
Create Date: 2026-05-21 08:50:52.468954

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '873624317ede'
down_revision = '7f2b8d9c1a34'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('category', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('products', 'category')
