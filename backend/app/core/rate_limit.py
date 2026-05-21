import logging
import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import settings
from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)


def rate_limit(
    limit: int | None = None,
    window_seconds: int | None = None,
) -> Callable:
    max_requests = limit or settings.RATE_LIMIT_DEFAULT_LIMIT
    window = window_seconds or settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS

    async def dependency(
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        bucket = int(time.time() // window)
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}:{request.url.path}:{bucket}"

        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)
        except Exception as exc:
            logger.warning("Rate limit unavailable for %s: %s", request.url.path, exc)
            return

        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
            )

    return dependency
