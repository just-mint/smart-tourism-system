<<<<<<< HEAD
from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser, SessionDep
from sqlalchemy import func, select
=======
import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic.networks import EmailStr
from redis.asyncio import Redis

from app.api.deps import get_current_active_superuser, SessionDep
from sqlalchemy import func, select, text
>>>>>>> origin/main
from app.models import User
from app.domains.culture.model import Place
from app.domains.inventory.model import Store, InventoryLock
from app.models import Message
from app.utils import generate_test_email, send_email

<<<<<<< HEAD
=======
logger = logging.getLogger(__name__)

>>>>>>> origin/main
router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
<<<<<<< HEAD
async def health_check() -> bool:
    return True
=======
async def health_check(session: SessionDep) -> JSONResponse:
    """
    Kiểm tra sức khỏe thực sự của hệ thống:
      - PostgreSQL: SELECT 1
      - Redis: PING
    Trả 200 nếu tất cả OK, 503 nếu bất kỳ service nào tạch.
    """
    status = {"postgres": "ok", "redis": "ok"}
    healthy = True

    # ── 1. PostgreSQL ──
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(f"[HealthCheck] PostgreSQL FAILED: {exc}")
        status["postgres"] = f"error: {exc}"
        healthy = False

    # ── 2. Redis ──
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        pong = await redis.ping()
        if not pong:
            raise ConnectionError("Redis PING returned False")
        await redis.aclose()
    except Exception as exc:
        logger.error(f"[HealthCheck] Redis FAILED: {exc}")
        status["redis"] = f"error: {exc}"
        healthy = False

    if not healthy:
        return JSONResponse(status_code=503, content={"status": "degraded", "checks": status})

    return JSONResponse(status_code=200, content={"status": "healthy", "checks": status})

>>>>>>> origin/main

@router.get("/telemetry/")
def get_telemetry(session: SessionDep) -> dict:
    active_users = session.scalar(select(func.count()).select_from(User))
    total_places = session.scalar(select(func.count()).select_from(Place))
    total_stores = session.scalar(select(func.count()).select_from(Store))
    active_locks = session.scalar(select(func.count()).select_from(InventoryLock))
    
    return {
        "active_users": active_users or 0,
        "total_places": total_places or 0,
        "total_stores": total_stores or 0,
        "active_locks": active_locks or 0,
    }
