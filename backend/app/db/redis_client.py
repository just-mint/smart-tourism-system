import os
from typing import AsyncGenerator

from redis.asyncio import Redis


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI Async Dependency: Tạo kết nối Redis asyncio cho mỗi request.
<<<<<<< HEAD
    Đọc REDIS_URL từ biến môi trường, mặc định là localhost:6379.
=======
    Đọc REDIS_URL từ biến môi trường. Docker Compose override qua env.
>>>>>>> origin/main
    Kết nối luôn được đóng trong finally block để tránh resource leak.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis: Redis = Redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,  # Tự decode bytes → str, tiện dùng với string keys
    )
    try:
        yield redis
    finally:
        await redis.aclose()
