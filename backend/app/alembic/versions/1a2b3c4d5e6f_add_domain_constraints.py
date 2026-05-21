"""Add domain constraints

Revision ID: 1a2b3c4d5e6f
Revises: 19138cb1625d
Create Date: 2026-05-15 23:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = '19138cb1625d'
branch_labels = None
depends_on = None

def upgrade():
    # 1. P1-09: Add Unique constraint for Inventory(store_id, product_id)
    op.create_unique_constraint('uq_inventory_store_product', 'inventory', ['store_id', 'product_id'])
    
    # 2. P1-09: Add Check constraints for stock, locked_stock, price
    op.create_check_constraint('check_stock_nonnegative', 'inventory', 'stock >= 0')
    op.create_check_constraint('check_locked_stock_nonnegative', 'inventory', 'locked_stock >= 0')
    op.create_check_constraint('check_price_nonnegative', 'products', 'price >= 0')
    
    # 3. P1-09: Add Check constraint for review rating (1-5)
    op.create_check_constraint('check_rating_range', 'reviews', 'rating >= 1 AND rating <= 5')

    # 4. P1-09: Add Foreign Key for reviews.place_id -> places.place_id
    op.create_foreign_key('fk_reviews_place_id', 'reviews', 'places', ['place_id'], ['place_id'])

    # 5. P1-10: Add GIN Trigram indexes for ILIKE queries
    op.execute('CREATE INDEX IF NOT EXISTS idx_stores_name_trgm ON stores USING gin (name gin_trgm_ops)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_stores_category_trgm ON stores USING gin (category gin_trgm_ops)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_products_desc_trgm ON products USING gin (description gin_trgm_ops)')

def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_products_desc_trgm')
    op.execute('DROP INDEX IF EXISTS idx_stores_category_trgm')
    op.execute('DROP INDEX IF EXISTS idx_stores_name_trgm')
    
    op.drop_constraint('fk_reviews_place_id', 'reviews', type_='foreignkey')
    op.drop_constraint('check_rating_range', 'reviews', type_='check')
    op.drop_constraint('check_price_nonnegative', 'products', type_='check')
    op.drop_constraint('check_locked_stock_nonnegative', 'inventory', type_='check')
    op.drop_constraint('check_stock_nonnegative', 'inventory', type_='check')
    op.drop_constraint('uq_inventory_store_product', 'inventory', type_='unique')
