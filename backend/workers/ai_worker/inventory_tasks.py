<<<<<<< HEAD
from workers.ai_worker.celery_app import celery_app
from sqlalchemy import create_engine
=======
"""
AEGIS O2O — Celery Beat Task: Sweep Expired Inventory Locks (P0-10 Fix)

Runs every 60 seconds via Celery Beat.
Idempotent: Uses SELECT … FOR UPDATE SKIP LOCKED to prevent double-release
across concurrent worker replicas.
"""

from workers.ai_worker.celery_app import celery_app
from sqlalchemy import create_engine, text
>>>>>>> origin/main
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

<<<<<<< HEAD
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/aegis_db")

@celery_app.task(name="workers.ai_worker.inventory_tasks.sweep_expired_locks")
def sweep_expired_locks():
    """
    Celery Beat Task — Chạy mỗi 60 giây.
    Tự động quét các inventory_locks hết hạn, hoàn trả tồn kho vào Postgres.
    Giải quyết vấn đề 'trigger-release bị thụ động'.
    """
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        from app.domains.inventory.service import check_and_release_expired_locks
        count = check_and_release_expired_locks(db)
        db.close()
        return {"released": count}
    except Exception as e:
        logger.error(f"[Celery Beat] Lỗi khi sweep locks: {e}")
        return {"error": str(e)}
=======
# ── Build DATABASE_URL from individual env vars (same as app Settings) ──
_PG_USER = os.getenv("POSTGRES_USER", "app")
_PG_PASS = os.getenv("POSTGRES_PASSWORD", "changethis")
_PG_HOST = os.getenv("POSTGRES_SERVER", "db")
_PG_PORT = os.getenv("POSTGRES_PORT", "5432")
_PG_DB = os.getenv("POSTGRES_DB", "app")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{_PG_USER}:{_PG_PASS}@{_PG_HOST}:{_PG_PORT}/{_PG_DB}",
)

# Inventory lock TTL (seconds) — must match app/core/config.py
LOCK_TTL_SECONDS = int(os.getenv("INVENTORY_LOCK_TTL", "900"))


@celery_app.task(
    name="workers.ai_worker.inventory_tasks.sweep_expired_locks",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def sweep_expired_locks(self):
    """
    Celery Beat Task — chạy mỗi 60 giây.

    Logic idempotent:
      1. Tìm tất cả InventoryLock có status='soft_locked' VÀ expires_at < NOW()
         (tức là đã vượt quá TTL cài sẵn, cộng thêm 1 phút grace period).
      2. Sử dụng FOR UPDATE SKIP LOCKED → nếu worker khác đang xử lý row
         thì bỏ qua, tránh double-release.
      3. Chuyển status → 'expired', giảm locked_stock tương ứng.
      4. Log metric rõ ràng.
    """
    engine = None
    session = None
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # ── BƯỚC 1: Lấy các lock hết hạn (idempotent với SKIP LOCKED) ──
        # Grace period: TTL + 1 phút (60 giây) đảm bảo không sweep lock
        # mà Redis vẫn đang giữ hợp lệ.
        expired_locks = (
            session.execute(
                text("""
                    SELECT id, product_id, quantity
                    FROM inventory_locks
                    WHERE status = 'soft_locked'
                      AND expires_at <= (NOW() - INTERVAL '1 minute')
                    FOR UPDATE SKIP LOCKED
                """)
            )
            .fetchall()
        )

        if not expired_locks:
            logger.debug("[Sweep Task] No expired locks found. Clean state.")
            return {"released": 0}

        released_count = 0
        lock_ids = []

        for lock_row in expired_locks:
            lock_id = lock_row[0]
            product_id = lock_row[1]
            quantity = lock_row[2]

            # ── BƯỚC 2: Giảm locked_stock (clamp tại 0) ──
            session.execute(
                text("""
                    UPDATE inventory
                    SET locked_stock = GREATEST(0, locked_stock - :qty)
                    WHERE product_id = :pid
                """),
                {"qty": quantity, "pid": product_id},
            )

            lock_ids.append(lock_id)
            released_count += 1

        # ── BƯỚC 3: Batch update status → 'expired' ──
        if lock_ids:
            session.execute(
                text("""
                    UPDATE inventory_locks
                    SET status = 'expired'
                    WHERE id = ANY(:ids)
                """),
                {"ids": lock_ids},
            )

        session.commit()
        logger.info(f"[Sweep Task] Released {released_count} expired locks.")
        return {"released": released_count}

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"[Sweep Task] Error during sweep: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e)
    finally:
        if session:
            session.close()
        if engine:
            engine.dispose()
>>>>>>> origin/main
