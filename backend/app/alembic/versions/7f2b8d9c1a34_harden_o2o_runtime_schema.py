"""harden_o2o_runtime_schema

Revision ID: 7f2b8d9c1a34
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-16 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7f2b8d9c1a34"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS price_override integer")
    op.execute("ALTER TABLE inventory_locks ADD COLUMN IF NOT EXISTS store_id integer")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_locks_store_id "
        "ON inventory_locks(store_id)"
    )
    op.execute("DROP INDEX IF EXISTS idx_active_locks")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_active_locks "
        "ON inventory_locks (expires_at) "
        "WHERE status IN ('soft_locked', 'active', 'checkout_pending')"
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'inventory_locks'
                  AND constraint_name = 'inventory_locks_store_id_fkey'
            ) THEN
                ALTER TABLE inventory_locks
                ADD CONSTRAINT inventory_locks_store_id_fkey
                FOREIGN KEY (store_id) REFERENCES stores(store_id);
            END IF;
        END $$;
    """)

    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'PENDING_PAYMENT'")
    op.execute("UPDATE orders SET status = 'PENDING_PAYMENT' WHERE status = 'PENDING_SHIP'")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS lock_id integer")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_lock_id ON orders(lock_id)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'orders'
                  AND constraint_name = 'orders_lock_id_fkey'
            ) THEN
                ALTER TABLE orders
                ADD CONSTRAINT orders_lock_id_fkey
                FOREIGN KEY (lock_id) REFERENCES inventory_locks(id);
            END IF;
        END $$;
    """)

    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding_model varchar(100)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding_version varchar(50)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS embedded_at timestamptz")
    op.execute("ALTER TABLE virtual_closets ADD COLUMN IF NOT EXISTS embedding_model varchar(100)")
    op.execute("ALTER TABLE virtual_closets ADD COLUMN IF NOT EXISTS embedding_version varchar(50)")
    op.execute("ALTER TABLE virtual_closets ADD COLUMN IF NOT EXISTS embedded_at timestamptz")

    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(order_id),
            provider VARCHAR(50) NOT NULL DEFAULT 'vietqr_mock',
            amount INTEGER NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'VND',
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            transaction_id VARCHAR(120),
            idempotency_key VARCHAR(120),
            raw_payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_payment_id ON payments(payment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_transaction_id "
        "ON payments(transaction_id) WHERE transaction_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_idempotency_key "
        "ON payments(idempotency_key) WHERE idempotency_key IS NOT NULL"
    )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'payments'
                  AND constraint_name = 'check_payment_amount_nonnegative'
            ) THEN
                ALTER TABLE payments
                ADD CONSTRAINT check_payment_amount_nonnegative CHECK (amount >= 0);
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS inventory_events (
            id SERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            entity_id VARCHAR(100) NOT NULL,
            user_id UUID,
            action VARCHAR(80) NOT NULL,
            payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_events_id ON inventory_events(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_events_entity_type ON inventory_events(entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_events_entity_id ON inventory_events(entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_events_action ON inventory_events(action)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_geom_geog "
        "ON places USING gist ((geom::geography))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_stores_geom_geog "
        "ON stores USING gist ((geom::geography))"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_stores_geom_geog")
    op.execute("DROP INDEX IF EXISTS idx_places_geom_geog")
    op.execute("DROP TABLE IF EXISTS inventory_events")
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("ALTER TABLE virtual_closets DROP COLUMN IF EXISTS embedded_at")
    op.execute("ALTER TABLE virtual_closets DROP COLUMN IF EXISTS embedding_version")
    op.execute("ALTER TABLE virtual_closets DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedded_at")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding_version")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'PENDING_SHIP'")
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_lock_id_fkey")
    op.execute("DROP INDEX IF EXISTS ix_orders_lock_id")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS lock_id")
    op.execute("ALTER TABLE inventory_locks DROP CONSTRAINT IF EXISTS inventory_locks_store_id_fkey")
    op.execute("DROP INDEX IF EXISTS idx_active_locks")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_active_locks "
        "ON inventory_locks (expires_at) "
        "WHERE status IN ('soft_locked', 'active')"
    )
    op.execute("DROP INDEX IF EXISTS ix_inventory_locks_store_id")
    op.execute("ALTER TABLE inventory_locks DROP COLUMN IF EXISTS store_id")
    op.execute("ALTER TABLE inventory DROP COLUMN IF EXISTS price_override")
