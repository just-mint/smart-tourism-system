from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import settings


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI Async Dependency: Tạo kết nối Redis asyncio cho mỗi request.
    Đọc REDIS_URL từ biến môi trường. Docker Compose override qua env.
    Kết nối luôn được đóng trong finally block để tránh resource leak.
    """
    redis: Redis = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,  # Tự decode bytes → str, tiện dùng với string keys
    )
    try:
        yield redis
    finally:
        await redis.aclose()
