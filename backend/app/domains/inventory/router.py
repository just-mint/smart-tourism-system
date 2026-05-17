"""
inventory/router.py — [13.3] Merchant/Catalog management REST API.

Tags:
  - catalog      → public endpoints (GET)
  - merchant     → merchant-only CRUD (requires is_merchant or superuser)
  - admin-catalog → superuser-only (categories, merchant role grant)
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from redis.asyncio import Redis
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.api.deps import get_current_user
from app.models import User
from app.domains.inventory import service, schema

router = APIRouter()

INTERNAL_SECRET_KEY = os.getenv("INTERNAL_SECRET_KEY", "")

# ─────────────────────────────────────────────────────────────
#  Auth helpers
# ─────────────────────────────────────────────────────────────

def verify_internal_or_superuser(
    x_internal_secret: str | None = Header(None),
    current_user: User | None = Depends(get_current_user),
) -> None:
    if INTERNAL_SECRET_KEY and x_internal_secret == INTERNAL_SECRET_KEY:
        return
    if current_user and current_user.is_superuser:
        return
    raise HTTPException(status_code=403, detail="Cần quyền Superuser hoặc Internal Secret.")


def require_merchant(current_user: User = Depends(get_current_user)) -> User:
    """Merchant hoặc superuser."""
    if current_user.is_merchant or current_user.is_superuser:
        return current_user
    raise HTTPException(status_code=403, detail="Bạn cần quyền Merchant để thực hiện thao tác này.")


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Chỉ Superuser mới có quyền này.")
    return current_user


# ═══════════════════════════════════════════════════════════════
#  [13.3] ProductCategory endpoints  — /inventory/categories
# ═══════════════════════════════════════════════════════════════

@router.get("/categories", response_model=list[schema.CategoryResponse], tags=["catalog"])
def get_categories(db: Session = Depends(get_db)):
    """Danh sách tất cả danh mục sản phẩm đang hoạt động."""
    return service.list_categories(db)


@router.get("/categories/{cat_id}", response_model=schema.CategoryResponse, tags=["catalog"])
def get_category(cat_id: int, db: Session = Depends(get_db)):
    return service.get_category(db, cat_id)


@router.post("/categories", response_model=schema.CategoryResponse, status_code=201, tags=["admin-catalog"])
def create_category(
    data: schema.CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """Tạo danh mục mới — chỉ Superuser."""
    return service.create_category(db, data)


@router.put("/categories/{cat_id}", response_model=schema.CategoryResponse, tags=["admin-catalog"])
def update_category(
    cat_id: int,
    data: schema.CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_superuser),
):
    return service.update_category(db, cat_id, data)


@router.delete("/categories/{cat_id}", status_code=204, tags=["admin-catalog"])
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_superuser),
):
    service.delete_category(db, cat_id)


# ═══════════════════════════════════════════════════════════════
#  [13.3] Store endpoints  — /inventory/stores
# ═══════════════════════════════════════════════════════════════

@router.get("/stores", response_model=list[schema.StoreResponse], tags=["catalog"])
def get_stores(
    place_id: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """Danh sách cửa hàng (lọc theo place_id hoặc lấy tất cả)."""
    return service.list_stores(db, place_id=place_id, active_only=active_only)


@router.get("/stores/{store_id}", response_model=schema.StoreDetailResponse, tags=["catalog"])
def get_store(store_id: int, db: Session = Depends(get_db)):
    return service.get_store(db, store_id)


@router.post("/stores", response_model=schema.StoreDetailResponse, status_code=201, tags=["merchant"])
def create_store(
    data: schema.StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Tạo cửa hàng mới — Merchant hoặc Superuser."""
    return service.create_store(db, data, owner_id=str(current_user.id))


@router.put("/stores/{store_id}", response_model=schema.StoreDetailResponse, tags=["merchant"])
def update_store(
    store_id: int,
    data: schema.StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Cập nhật cửa hàng — chỉ chủ cửa hàng hoặc Superuser."""
    return service.update_store(db, store_id, data, str(current_user.id), current_user.is_superuser)


@router.delete("/stores/{store_id}", status_code=204, tags=["merchant"])
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Xoá mềm cửa hàng."""
    service.delete_store(db, store_id, str(current_user.id), current_user.is_superuser)


@router.post("/stores/{store_id}/image", response_model=schema.StoreDetailResponse, tags=["merchant"])
def upload_store_image(
    store_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Upload ảnh bìa cửa hàng."""
    return service.upload_store_image(db, store_id, file, str(current_user.id), current_user.is_superuser)


# ── Store hours shortcut ──────────────────────────────────────

@router.put("/stores/{store_id}/hours", response_model=schema.StoreDetailResponse, tags=["merchant"])
def set_store_hours(
    store_id: int,
    hours: dict,   # {"mon":{"open":"08:00","close":"22:00"}, ...}
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Cập nhật giờ mở cửa theo từng ngày trong tuần."""
    return service.update_store(
        db, store_id, schema.StoreUpdate(opening_hours=hours),
        str(current_user.id), current_user.is_superuser,
    )


# ═══════════════════════════════════════════════════════════════
#  [13.3] Product endpoints  — /inventory/products
# ═══════════════════════════════════════════════════════════════

@router.get("/products", response_model=list[schema.ProductResponse], tags=["catalog"])
def get_products(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Danh sách sản phẩm (tuỳ chọn: lọc theo store)."""
    return service.list_products(db, store_id=store_id)


@router.get("/products/{product_id}", response_model=schema.ProductResponse, tags=["catalog"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_by_id(db, product_id)


@router.post("/products", response_model=schema.ProductResponse, status_code=201, tags=["merchant"])
def create_product(
    data: schema.ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_merchant),
):
    """Tạo sản phẩm mới."""
    return service.create_product(db, data)


@router.put("/products/{product_id}", response_model=schema.ProductResponse, tags=["merchant"])
def update_product(
    product_id: int,
    data: schema.ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_merchant),
):
    """Cập nhật sản phẩm (tên/description → tự kích hoạt lại embedding)."""
    return service.update_product(db, product_id, data)


@router.delete("/products/{product_id}", status_code=204, tags=["merchant"])
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_merchant),
):
    service.delete_product(db, product_id)


@router.post("/products/{product_id}/image", response_model=schema.ProductResponse, tags=["merchant"])
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_merchant),
):
    """Upload / thay ảnh sản phẩm — tự reset embedding_status → pending."""
    return service.upload_product_image(db, product_id, file)


# ═══════════════════════════════════════════════════════════════
#  [13.3] Store-Product inventory link  — /inventory/stores/{id}/inventory
# ═══════════════════════════════════════════════════════════════

@router.get("/stores/{store_id}/products", response_model=list[schema.ProductResponse], tags=["catalog"])
def get_store_products(store_id: int, db: Session = Depends(get_db)):
    return service.get_products_by_store(db, store_id)


@router.put("/stores/{store_id}/inventory", response_model=schema.InventoryResponse, tags=["merchant"])
def upsert_store_inventory(
    store_id: int,
    data: schema.InventoryUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    """Thêm / cập nhật sản phẩm trong kho của cửa hàng (kể cả giá riêng store_price)."""
    return service.upsert_inventory(db, store_id, data, str(current_user.id), current_user.is_superuser)


@router.delete("/stores/{store_id}/inventory/{product_id}", status_code=204, tags=["merchant"])
def remove_store_inventory(
    store_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    service.remove_inventory(db, store_id, product_id, str(current_user.id), current_user.is_superuser)


# ═══════════════════════════════════════════════════════════════
#  [13.3] Faceted Search  — /inventory/search
# ═══════════════════════════════════════════════════════════════

@router.get("/search", response_model=schema.FacetedSearchResult, tags=["catalog"])
def search(
    q: str = "",
    category_id: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius: int = 5000,
    in_stock_only: bool = False,
    sort: str = "relevance",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Tìm kiếm có facets: lọc theo giá, danh mục, khoảng cách, tình trạng hàng.
    - sort: relevance | price_asc | price_desc | distance
    """
    facets = schema.SearchFacets(
        q=q, category_id=category_id,
        min_price=min_price, max_price=max_price,
        lat=lat, lon=lon, radius=radius,
        in_stock_only=in_stock_only,
        sort=sort, page=page, page_size=page_size,
    )
    return service.faceted_search(db, facets)


# ═══════════════════════════════════════════════════════════════
#  Price comparison (existing, updated)
# ═══════════════════════════════════════════════════════════════

@router.get("/products/{product_id}/compare", tags=["catalog"])
def compare_prices(
    product_id: int,
    store_id: int,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """So sánh giá sản phẩm tại nhiều cửa hàng — kể cả store_price override."""
    return service.compare_product_prices(db, product_id, store_id, lat, lon)


# ═══════════════════════════════════════════════════════════════
#  Inventory lock / order (existing, unchanged API surface)
# ═══════════════════════════════════════════════════════════════

@router.post("/lock", response_model=dict, tags=["catalog"])
async def create_inventory_lock(
    request: schema.LockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    lock = await service.create_lock(db=db, redis=redis, request=request, user_id=current_user.id)
    return {"message": "Soft-lock thành công", "lock_id": lock.id, "expires_at": lock.expires_at}


@router.get("/locks", response_model=list[schema.LockResponseItem], tags=["catalog"])
async def get_my_locks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.get_user_locks_with_ttl(db=db, redis=redis, user_id=current_user.id)


@router.post("/trigger-release", dependencies=[Depends(verify_internal_or_superuser)], tags=["admin-catalog"])
def release_expired(db: Session = Depends(get_db)):
    count = service.check_and_release_expired_locks(db=db)
    return {"message": f"Hoàn trả tồn kho cho {count} lock hết hạn."}


@router.post("/orders", response_model=schema.OrderResponse, tags=["catalog"])
async def create_order(
    data: schema.OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.finalize_order(db=db, redis=redis, data=data, user_id=current_user.id)


# ═══════════════════════════════════════════════════════════════
#  [13.3] Admin: grant / revoke merchant role
# ═══════════════════════════════════════════════════════════════

@router.patch("/admin/users/{user_id}/merchant", tags=["admin-catalog"])
def set_merchant_role(
    user_id: str,
    is_merchant: bool,
    db: Session = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """Superuser cấp / thu hồi quyền Merchant cho user."""
    from sqlmodel import Session as SQLModelSession, select
    from app.models import User as UserModel
    from app.core.db import engine

    with SQLModelSession(engine) as s:
        user = s.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User không tồn tại")
        user.is_merchant = is_merchant
        s.add(user)
        s.commit()
        s.refresh(user)
        return {"user_id": str(user.id), "is_merchant": user.is_merchant, "email": user.email}
