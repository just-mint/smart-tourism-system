"""sync_domain_schema_v2

Revision ID: 1945bf0afe56
Revises: fe56fa70289e
Create Date: 2026-05-14 19:15:58.801026

Sync schema sau khi b3c7e9f1a2d4 tạo domain tables.
Migration này chỉ áp dụng các alter idempotent-safe:
  - Đổi inventory_locks.user_id từ INTEGER sang UUID (nếu chưa đổi)
  - Đảm bảo inventory có FK đúng tên mới
  - Đảm bảo ix_ indexes tiêu chuẩn tồn tại (IF NOT EXISTS qua raw SQL)
Không create bảng (đã có từ b3c7e9f1a2d4).
Không drop index/constraint không tồn tại trong fresh DB.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1945bf0afe56'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    # ── Đảm bảo inventory_locks.user_id là UUID (idempotent) ─────────────────
    # Trên fresh DB (b3c7e9f1a2d4), cột này đã là UUID từ đầu → skip nếu đúng rồi
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name='inventory_locks' AND column_name='user_id'
    """)).fetchone()
    if result and result[0].lower() == 'integer':
        op.alter_column(
            'inventory_locks', 'user_id',
            existing_type=sa.INTEGER(),
            type_=sa.UUID(),
            existing_nullable=False,
            postgresql_using="user_id::text::uuid"
        )

    # ── Đảm bảo FK inventory có tên chuẩn mới (idempotent) ──────────────────
    # Thử rename FK cũ → mới; bỏ qua nếu FK cũ không tồn tại
    fk_check = conn.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name='inventory' AND constraint_type='FOREIGN KEY'
        AND constraint_name='inventory_store_id_fkey'
    """)).fetchone()
    if fk_check:
        op.drop_constraint('inventory_store_id_fkey', 'inventory', type_='foreignkey')
        op.create_foreign_key(
            'inventory_store_id_fkey_new', 'inventory', 'stores',
            ['store_id'], ['store_id']
        )

    fk_check2 = conn.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name='inventory' AND constraint_type='FOREIGN KEY'
        AND constraint_name='inventory_product_id_fkey'
    """)).fetchone()
    if fk_check2:
        op.drop_constraint('inventory_product_id_fkey', 'inventory', type_='foreignkey')
        op.create_foreign_key(
            'inventory_product_id_fkey_new', 'inventory', 'products',
            ['product_id'], ['product_id']
        )

    # ── Đảm bảo orders table tồn tại (IF NOT EXISTS — idempotent) ────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            store_id INTEGER REFERENCES stores(store_id),
            quantity INTEGER NOT NULL DEFAULT 1,
            total_amount INTEGER NOT NULL DEFAULT 0,
            full_name VARCHAR(255) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            address TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING_SHIP',
            order_code VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_code ON orders(order_code)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_orders_order_id ON orders(order_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id)"
    ))


def downgrade():
    # Không rollback FK rename (an toàn để lại)
    pass
