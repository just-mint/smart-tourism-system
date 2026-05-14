from workers.ai_worker.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

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
