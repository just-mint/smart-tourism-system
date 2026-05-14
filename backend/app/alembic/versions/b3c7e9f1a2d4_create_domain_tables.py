"""create_domain_tables

Revision ID: b3c7e9f1a2d4
Revises: 1a31ce608336
Create Date: 2026-05-14 22:05:00.000000

Tạo toàn bộ domain tables từ đầu (places, reviews, stores, products,
inventory, inventory_locks, orders, vision_tasks, virtual_closets).
Migration này được chèn vào giữa chuỗi:
    1a31ce608336 → b3c7e9f1a2d4 → fe56fa70289e → 1945bf0afe56
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c7e9f1a2d4'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # ── 0. Đảm bảo extensions tồn tại ──────────────────────────────────────
    # (Idempotent — an toàn khi chạy lại; init_db.sql đã làm việc này
    #  ở boot time, nhưng thêm ở đây để migration tự đủ khi chạy offline)
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── 1. places ────────────────────────────────────────────────────────────
    op.create_table(
        'places',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('place_id', sa.String(length=50), nullable=True),
        sa.Column('place_type', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('lat', sa.Numeric(), nullable=True),
        sa.Column('lon', sa.Numeric(), nullable=True),
        # geoalchemy2 geometry — stored as text type for Alembic portability
        sa.Column('geom', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_places_id'), 'places', ['id'], unique=False)
    op.create_index(op.f('ix_places_place_id'), 'places', ['place_id'], unique=True)
    op.create_index(op.f('ix_places_category'), 'places', ['category'], unique=False)
    # GIN trigram indexes for full-text search
    op.create_index(
        'idx_places_name_trgm', 'places', ['name'],
        postgresql_using='gin',
        postgresql_ops={'name': 'gin_trgm_ops'},
    )
    op.create_index(
        'idx_places_category_trgm', 'places', ['category'],
        postgresql_using='gin',
        postgresql_ops={'category': 'gin_trgm_ops'},
    )
    # GiST spatial index
    op.create_index('idx_places_geom', 'places', ['geom'], postgresql_using='gist')

    # ── 2. reviews ───────────────────────────────────────────────────────────
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('place_id', sa.String(length=50), nullable=True),
        sa.Column('author_name', sa.String(length=100), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('time_posted', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_place_id'), 'reviews', ['place_id'], unique=False)

    # ── 3. stores ────────────────────────────────────────────────────────────
    op.create_table(
        'stores',
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('place_id', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('lat', sa.Numeric(), nullable=True),
        sa.Column('lon', sa.Numeric(), nullable=True),
        sa.Column('geom', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=1), nullable=True,
                  server_default=sa.text('0.0')),
        sa.PrimaryKeyConstraint('store_id'),
    )
    op.create_index(op.f('ix_stores_store_id'), 'stores', ['store_id'], unique=False)
    op.create_index('idx_stores_geom', 'stores', ['geom'], postgresql_using='gist')

    # ── 4. products ──────────────────────────────────────────────────────────
    op.create_table(
        'products',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('original_price', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        # pgvector column — use raw SQL DDL to avoid SQLAlchemy type issue
        sa.Column('embedding', sa.Text(), nullable=True),  # placeholder, replaced below
        sa.Column('size', sa.String(length=20), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('product_id'),
    )
    # Drop placeholder and create real vector column
    op.drop_column('products', 'embedding')
    op.execute('ALTER TABLE products ADD COLUMN embedding vector(512)')
    op.create_index(op.f('ix_products_product_id'), 'products', ['product_id'], unique=False)
    # HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_embedding "
        "ON products USING hnsw (embedding vector_cosine_ops)"
    )

    # ── 5. inventory ─────────────────────────────────────────────────────────
    op.create_table(
        'inventory',
        sa.Column('inventory_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('locked_stock', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'],
                                name='inventory_product_id_fkey_new'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'],
                                name='inventory_store_id_fkey_new'),
        sa.PrimaryKeyConstraint('inventory_id'),
    )
    op.create_index(op.f('ix_inventory_inventory_id'), 'inventory', ['inventory_id'], unique=False)

    # ── 6. inventory_locks ───────────────────────────────────────────────────
    op.create_table(
        'inventory_locks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + interval '15 minutes'")),
        sa.Column('status', sa.String(length=50), nullable=False,
                  server_default=sa.text("'soft_locked'")),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_locks_id'), 'inventory_locks', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_locks_user_id'), 'inventory_locks', ['user_id'], unique=False)
    # Partial index for active locks
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_active_locks "
        "ON inventory_locks (expires_at) "
        "WHERE status IN ('soft_locked', 'active')"
    )

    # ── 7. orders ────────────────────────────────────────────────────────────
    op.create_table(
        'orders',
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('total_amount', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False,
                  server_default=sa.text("'PENDING_SHIP'")),
        sa.Column('order_code', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id']),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id']),
        sa.PrimaryKeyConstraint('order_id'),
    )
    op.create_index(op.f('ix_orders_order_id'), 'orders', ['order_id'], unique=False)
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'], unique=False)
    op.create_index(op.f('ix_orders_order_code'), 'orders', ['order_code'], unique=True)

    # ── 8. vision_tasks ──────────────────────────────────────────────────────
    op.create_table(
        'vision_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=False),
        sa.Column('image_path', sa.String(length=1000), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False,
                  server_default=sa.text("'processing'")),
        sa.Column('detected_objects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matched_product_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id'),
    )
    op.create_index(op.f('ix_vision_tasks_id'), 'vision_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_vision_tasks_task_id'), 'vision_tasks', ['task_id'], unique=False)

    # ── 9. virtual_closets ───────────────────────────────────────────────────
    op.create_table(
        'virtual_closets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_path', sa.String(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_virtual_closets_id'), 'virtual_closets', ['id'], unique=False)
    op.create_index(op.f('ix_virtual_closets_user_id'), 'virtual_closets', ['user_id'], unique=False)
    # HNSW index for virtual closet embeddings (column added separately)
    op.execute('ALTER TABLE virtual_closets ADD COLUMN vector_embedding vector(512)')
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_virtual_closets_embedding "
        "ON virtual_closets USING hnsw (vector_embedding vector_cosine_ops)"
    )


def downgrade():
    # Drop trong thứ tự ngược — FK dependencies trước
    op.execute('DROP INDEX IF EXISTS idx_virtual_closets_embedding')
    op.drop_table('virtual_closets')

    op.drop_table('vision_tasks')

    op.drop_index(op.f('ix_orders_order_code'), table_name='orders')
    op.drop_index(op.f('ix_orders_user_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_order_id'), table_name='orders')
    op.drop_table('orders')

    op.execute('DROP INDEX IF EXISTS idx_active_locks')
    op.drop_index(op.f('ix_inventory_locks_user_id'), table_name='inventory_locks')
    op.drop_index(op.f('ix_inventory_locks_id'), table_name='inventory_locks')
    op.drop_table('inventory_locks')

    op.drop_index(op.f('ix_inventory_inventory_id'), table_name='inventory')
    op.drop_table('inventory')

    op.execute('DROP INDEX IF EXISTS idx_products_embedding')
    op.drop_index(op.f('ix_products_product_id'), table_name='products')
    op.drop_table('products')

    op.drop_index('idx_stores_geom', table_name='stores')
    op.drop_index(op.f('ix_stores_store_id'), table_name='stores')
    op.drop_table('stores')

    op.drop_index(op.f('ix_reviews_place_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_id'), table_name='reviews')
    op.drop_table('reviews')

    op.drop_index('idx_places_geom', table_name='places')
    op.drop_index('idx_places_category_trgm', table_name='places')
    op.drop_index('idx_places_name_trgm', table_name='places')
    op.drop_index(op.f('ix_places_category'), table_name='places')
    op.drop_index(op.f('ix_places_place_id'), table_name='places')
    op.drop_index(op.f('ix_places_id'), table_name='places')
    op.drop_table('places')
