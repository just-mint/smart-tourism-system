"""merchant_catalog_schema_v13_3

Revision ID: a1b2c3d4e5f6
Revises: b3c7e9f1a2d4
Create Date: 2026-05-17 19:00:00.000000

[13.3] Merchant/Store management schema additions:
  - product_categories table (normalised taxonomy)
  - stores: owner_id, is_active, description, image_url, opening_hours (JSONB),
            service_radius, created_at, updated_at
  - products: category_id (FK), sku (unique), is_active, updated_at
  - inventory: store_price, is_available
  - user: is_merchant flag
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '19138cb1625d'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. product_categories ─────────────────────────────────────────────────
    op.create_table(
        'product_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('icon_url', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parent_id'], ['product_categories.id'],
                                name='fk_category_parent'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_category_name'),
        sa.UniqueConstraint('slug', name='uq_category_slug'),
    )
    op.create_index('ix_product_categories_id', 'product_categories', ['id'])

    # ── 2. stores — new columns ───────────────────────────────────────────────
    op.add_column('stores', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('stores', sa.Column('image_url', sa.Text(), nullable=True))
    op.add_column('stores', sa.Column('owner_id',
                  postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('stores', sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')))
    op.add_column('stores', sa.Column('opening_hours',
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('stores', sa.Column('service_radius', sa.Integer(), nullable=True,
                  server_default=sa.text('2000')))
    op.add_column('stores', sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=True, server_default=sa.text('now()')))
    op.add_column('stores', sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=True))
    op.create_index('ix_stores_owner_id', 'stores', ['owner_id'])

    # ── 3. products — new columns ─────────────────────────────────────────────
    op.add_column('products', sa.Column('sku', sa.String(length=100), nullable=True))
    op.add_column('products', sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=True))

    # embedding_status: may not exist yet in older envs
    op.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS embedding_status varchar(50) DEFAULT 'pending'
    """)

    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_unique_constraint('uq_products_sku', 'products', ['sku'])
    op.create_foreign_key(
        'fk_products_category_id',
        'products', 'product_categories',
        ['category_id'], ['id'],
    )

    # GIN trigram index for product name search
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_products_name_trgm '
        'ON products USING gin (name gin_trgm_ops)'
    )

    # ── 4. inventory — new columns ────────────────────────────────────────────
    op.add_column('inventory', sa.Column('store_price', sa.Integer(), nullable=True))
    op.add_column('inventory', sa.Column('is_available', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')))

    # ── 5. user — merchant flag ───────────────────────────────────────────────
    op.add_column('user', sa.Column('is_merchant', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')))

    # ── 6. Seed 8 default categories ─────────────────────────────────────────
    op.execute("""
        INSERT INTO product_categories (name, slug, sort_order) VALUES
        ('Thời trang', 'thoi-trang', 1),
        ('Ẩm thực & Đặc sản', 'am-thuc-dac-san', 2),
        ('Đồ lưu niệm', 'do-luu-niem', 3),
        ('Mỹ phẩm & Chăm sóc', 'my-pham-cham-soc', 4),
        ('Điện tử & Phụ kiện', 'dien-tu-phu-kien', 5),
        ('Sách & Văn phòng phẩm', 'sach-van-phong-pham', 6),
        ('Thể thao & Du lịch', 'the-thao-du-lich', 7),
        ('Khác', 'khac', 99)
        ON CONFLICT (slug) DO NOTHING
    """)


def downgrade():
    # Reverse in opposite order
    op.execute("DELETE FROM product_categories WHERE slug IN ('thoi-trang','am-thuc-dac-san','do-luu-niem','my-pham-cham-soc','dien-tu-phu-kien','sach-van-phong-pham','the-thao-du-lich','khac')")

    op.drop_column('user', 'is_merchant')

    op.drop_column('inventory', 'is_available')
    op.drop_column('inventory', 'store_price')

    op.execute('DROP INDEX IF EXISTS idx_products_name_trgm')
    op.drop_constraint('fk_products_category_id', 'products', type_='foreignkey')
    op.drop_constraint('uq_products_sku', 'products', type_='unique')
    op.drop_index('ix_products_category_id', 'products')
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'is_active')
    op.drop_column('products', 'category_id')
    op.drop_column('products', 'sku')

    op.drop_index('ix_stores_owner_id', 'stores')
    op.drop_column('stores', 'updated_at')
    op.drop_column('stores', 'created_at')
    op.drop_column('stores', 'service_radius')
    op.drop_column('stores', 'opening_hours')
    op.drop_column('stores', 'is_active')
    op.drop_column('stores', 'owner_id')
    op.drop_column('stores', 'image_url')
    op.drop_column('stores', 'description')

    op.drop_index('ix_product_categories_id', 'product_categories')
    op.drop_table('product_categories')
