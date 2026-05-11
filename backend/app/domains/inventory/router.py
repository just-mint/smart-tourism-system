from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from redis.asyncio import Redis
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.api.deps import get_current_user
from app.models import User
from app.domains.inventory import service, schema

router = APIRouter()

@router.get("/stores", response_model=list[schema.StoreResponse])
def get_stores(place_id: str | None = None, db: Session = Depends(get_db)):
    return service.get_all_stores(db=db, place_id=place_id)

@router.get("/products/{id}", response_model=schema.ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    prod = service.get_product_by_id(db=db, product_id=id)
    if not prod: raise HTTPException(status_code=404, detail="Không thấy Product")
    return prod

@router.get("/stores/{store_id}/products", response_model=list[schema.ProductResponse])
def get_store_products(store_id: int, db: Session = Depends(get_db)):
    return service.get_products_by_store(db=db, store_id=store_id)

@router.post("/lock", response_model=dict)
async def create_inventory_lock(request: schema.LockRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), redis: Redis = Depends(get_redis)):
    """API Phân tầng: Chạm phanh Redis trước, Lock Postgres sau. An toàn giữ hàng O2O."""
    lock = await service.create_lock(db=db, redis=redis, request=request, user_id=current_user.id)
    return {"message": "Đã chặn (Soft-lock) thành công trong 15 phút đa Server", "lock_id": lock.id, "expires_at": lock.expires_at}

@router.get("/locks", response_model=list[schema.LockResponseItem])
async def get_my_locks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), redis: Redis = Depends(get_redis)):
    """Tra cứu Giỏ hàng & Đồng hồ đếm ngược được nuôi bởi Redis"""
    return await service.get_user_locks_with_ttl(db=db, redis=redis, user_id=current_user.id)

@router.post("/trigger-release")
def release_expired(db: Session = Depends(get_db)):
    """API Dọn dẹp Cronjob trả lại hàng vào Database khi thời lượng Redis bốc hơi"""
    count = service.check_and_release_expired_locks(db=db)
    return {"message": f"Hệ thống đã tự động hoàn trả tồn kho cho {count} giao dịch không thanh toán."}


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
        db=db, product_id=product_id, current_store_id=store_id,
        lat=lat, lon=lon,
    )
