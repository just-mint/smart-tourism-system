import os

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from jwt.exceptions import InvalidTokenError
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, reusable_oauth2
from app.core import security
from app.core.config import settings
from app.db.redis_client import get_redis
from app.db.session import get_db
from app.domains.inventory import schema, service
from app.models import TokenPayload, User

router = APIRouter()

# ── Internal Secret cho service-to-service / Celery calls ──
INTERNAL_SECRET_KEY = os.getenv("INTERNAL_SECRET_KEY", "")


def verify_internal_or_superuser(
    request: Request,
    x_internal_secret: str | None = Header(None),
    token: str | None = Depends(reusable_oauth2),
    db: Session = Depends(get_db),
) -> None:
    """
    Bảo mật 2 lớp cho endpoint nội bộ:
      1. Header X-Internal-Secret khớp INTERNAL_SECRET_KEY → OK (Celery/Cronjob gọi).
      2. Hoặc User đã đăng nhập VÀ là superuser → OK (Admin gọi thủ công).
    Nếu không thỏa cả 2 → 403.
    """
    # Lớp 1: Internal secret header
    if INTERNAL_SECRET_KEY and x_internal_secret == INTERNAL_SECRET_KEY:
        return

    # Lớp 2: Superuser check
    current_user = None
    actual_token = token or request.cookies.get("access_token")
    if actual_token:
        try:
            payload = jwt.decode(
                actual_token,
                settings.SECRET_KEY,
                algorithms=[security.ALGORITHM],
            )
            token_data = TokenPayload(**payload)
            current_user = db.get(User, token_data.sub) if token_data.sub else None
        except InvalidTokenError:
            current_user = None

    if current_user and current_user.is_superuser:
        return

    raise HTTPException(
        status_code=403,
        detail="Bạn không có quyền gọi endpoint này. Cần quyền Superuser hoặc Internal Secret hợp lệ.",
    )


@router.get("/stores", response_model=list[schema.StoreResponse])
def get_stores(place_id: str | None = None, db: Session = Depends(get_db)):
    return service.get_all_stores(db=db, place_id=place_id)


@router.get("/products/{id}", response_model=schema.ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    prod = service.get_product_by_id(db=db, product_id=id)
    if not prod:
        raise HTTPException(status_code=404, detail="Không thấy Product")
    return prod


@router.get("/stores/{store_id}/products", response_model=list[schema.ProductResponse])
def get_store_products(store_id: int, db: Session = Depends(get_db)):
    return service.get_products_by_store(db=db, store_id=store_id)


@router.get("/search", response_model=schema.SearchResult)
def search(q: str = "", db: Session = Depends(get_db)):
    """Tìm kiếm tổng hợp: Store + Product theo keyword"""
    if not q or len(q.strip()) < 1:
        return {"stores": [], "products": []}
    return service.search_stores_and_products(db=db, query=q.strip())


@router.post("/lock", response_model=dict)
async def create_inventory_lock(
    request: schema.LockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """API Phân tầng: Chạm phanh Redis trước, Lock Postgres sau. An toàn giữ hàng O2O."""
    lock = await service.create_lock(
        db=db, redis=redis, request=request, user_id=current_user.id
    )
    return {
        "message": "Đã chặn (Soft-lock) thành công trong 15 phút đa Server",
        "lock_id": lock.id,
        "expires_at": lock.expires_at,
    }


@router.get("/locks", response_model=list[schema.LockResponseItem])
async def get_my_locks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Tra cứu Giỏ hàng & Đồng hồ đếm ngược được nuôi bởi Redis"""
    return await service.get_user_locks_with_ttl(
        db=db, redis=redis, user_id=current_user.id
    )


@router.delete("/locks/{lock_id}", response_model=dict)
async def cancel_my_lock(
    lock_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    await service.cancel_lock(
        db=db, redis=redis, lock_id=lock_id, user_id=current_user.id
    )
    return {"message": "Đã hủy giữ hàng."}


@router.post("/trigger-release", dependencies=[Depends(verify_internal_or_superuser)])
def release_expired(db: Session = Depends(get_db)):
    """API Dọn dẹp (Bảo mật): Trả lại hàng vào DB khi lock hết hạn. Chỉ Superuser hoặc Internal Service gọi được."""
    count = service.check_and_release_expired_locks(db=db)
    return {
        "message": f"Hệ thống đã tự động hoàn trả tồn kho cho {count} giao dịch không thanh toán."
    }


@router.get("/products/{product_id}/compare")
def compare_prices(
    product_id: int,
    store_id: int,
    lat: float | None = None,
    lon: float | None = None,
    db: Session = Depends(get_db),
):
    """So sánh giá sản phẩm tại nhiều cửa hàng gần nhau — dùng cho PriceCompareModal"""
    return service.compare_product_prices(
        db=db,
        product_id=product_id,
        current_store_id=store_id,
        lat=lat,
        lon=lon,
    )


@router.post("/orders", response_model=schema.OrderResponse)
async def create_order(
    data: schema.OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Hoàn tất đơn hàng O2O: Xóa Redis Lock → Trừ tồn kho → Tạo Order → Trả VietQR"""
    return await service.finalize_order(
        db=db, redis=redis, data=data, user_id=current_user.id
    )


@router.get("/orders/me", response_model=list[schema.OrderDetailResponse])
def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách đơn hàng của tôi"""
    return service.get_user_orders(db=db, user_id=current_user.id)


@router.get("/orders/{order_id}", response_model=schema.OrderDetailResponse)
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết đơn hàng"""
    return service.get_order(db=db, order_id=order_id, user_id=current_user.id)


@router.post("/orders/{order_id}/cancel", response_model=dict)
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hủy đơn hàng và giải phóng tồn kho"""
    service.cancel_order(db=db, order_id=order_id, user_id=current_user.id)
    return {"message": "Đã hủy đơn hàng thành công"}


@router.post("/payments/webhook", response_model=schema.PaymentWebhookResponse)
def payment_webhook(
    data: schema.PaymentWebhook,
    db: Session = Depends(get_db),
):
    """Webhook payment: verify HMAC signature, idempotency, then update order state."""
    return service.handle_payment_webhook(db=db, data=data)
