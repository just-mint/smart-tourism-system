"""add_domain_indexes_and_extensions

Revision ID: 19138cb1625d
Revises: 1945bf0afe56
Create Date: 2026-05-15 01:27:22.448386

Thêm phần còn thiếu sau sync_domain_schema_v2:
  - Đảm bảo 4 extensions tồn tại (idempotent)
  - GIN trigram indexes: idx_places_name_trgm, idx_products_name_trgm
  - HNSW vector indexes: idx_products_embedding_hnsw, idx_virtual_closets_vector_hnsw
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '19138cb1625d'
down_revision = '1945bf0afe56'
branch_labels = None
depends_on = None


def upgrade():
    # ── Extensions (idempotent — an toàn khi chạy lại) ───────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # ── GIN trigram indexes cho full-text search ──────────────────────────────
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_places_name_trgm '
        'ON places USING gin (name gin_trgm_ops)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_products_name_trgm '
        'ON products USING gin (name gin_trgm_ops)'
    )

    # ── HNSW vector indexes cho similarity search ─────────────────────────────
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw '
        'ON products USING hnsw (embedding vector_cosine_ops)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_virtual_closets_vector_hnsw '
        'ON virtual_closets USING hnsw (vector_embedding vector_cosine_ops)'
    )


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_virtual_closets_vector_hnsw')
    op.execute('DROP INDEX IF EXISTS idx_products_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS idx_products_name_trgm')
    op.execute('DROP INDEX IF EXISTS idx_places_name_trgm')
    # Extensions KHÔNG drop ở đây vì có thể dùng bởi data đang tồn tại
