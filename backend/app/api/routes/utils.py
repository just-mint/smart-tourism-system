import json
import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic.networks import EmailStr
from redis.asyncio import Redis
from sqlalchemy import func, select, text

from app.api.deps import SessionDep, get_current_active_superuser
from app.domains.culture.model import Place
from app.domains.inventory.model import InventoryLock, Store
from app.models import Message, User
from app.utils import generate_test_email, send_email

logger = logging.getLogger(__name__)

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

@router.get("/telemetry/", dependencies=[Depends(get_current_active_superuser)])
async def get_telemetry(session: SessionDep) -> dict:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    cached = await redis.get("telemetry_data")
    if cached:
        await redis.aclose()
        return json.loads(cached)

    active_users = session.scalar(select(func.count()).select_from(User))
    total_places = session.scalar(select(func.count()).select_from(Place))
    total_stores = session.scalar(select(func.count()).select_from(Store))
    active_locks = session.scalar(select(func.count()).select_from(InventoryLock))

    data = {
        "active_users": active_users or 0,
        "total_places": total_places or 0,
        "total_stores": total_stores or 0,
        "active_locks": active_locks or 0,
    }

    await redis.set("telemetry_data", json.dumps(data), ex=300)
    await redis.aclose()

    return data
