import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_worker",
    broker=RABBITMQ_URL,
    backend=REDIS_URL,  # Dùng Redis làm result backend (tốt hơn RPC)
    include=[
        "workers.ai_worker.vision_tasks",
        "workers.ai_worker.inventory_tasks",  # Cronjob dọn dẹp locks
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# === CELERY BEAT SCHEDULE — Cronjob tự động ===
celery_app.conf.beat_schedule = {
    # Chạy mỗi 60 giây: quét và giải phóng các inventory lock hết hạn
    "release-expired-locks-every-minute": {
        "task": "workers.ai_worker.inventory_tasks.sweep_expired_locks",
        "schedule": 60.0,  # Giây
    },
}
