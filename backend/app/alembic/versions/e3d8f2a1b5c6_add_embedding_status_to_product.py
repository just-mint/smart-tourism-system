"""add_embedding_status_to_product

Revision ID: e3d8f2a1b5c6
Revises: 1945bf0afe56
Create Date: 2026-05-16 23:56:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3d8f2a1b5c6'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('embedding_status', sa.String(length=50), nullable=True, server_default='pending'))


def downgrade():
    op.drop_column('products', 'embedding_status')
