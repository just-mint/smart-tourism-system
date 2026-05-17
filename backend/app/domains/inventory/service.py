"""
inventory/service.py — [13.3] Merchant/Catalog management service layer.
"""
from __future__ import annotations

import logging
import os
import random
import string
import urllib.parse
import uuid as uuid_lib
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.domains.inventory.model import (
    Inventory, InventoryLock, Order, Product, ProductCategory, Store,
)
from app.domains.inventory.schema import (
    CategoryCreate, CategoryUpdate,
    InventoryUpsert, LockRequest, OrderCreate,
    ProductCreate, ProductUpdate,
    SearchFacets,
    StoreCreate, StoreUpdate,
)
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/static/uploads")


def _save_upload(file: UploadFile, sub: str = "products") -> str:
    """Lưu file upload vào UPLOAD_DIR và trả về URL tương đối."""
    dest = os.path.join(UPLOAD_DIR, sub)
    os.makedirs(dest, exist_ok=True)
    ext = os.path.splitext(file.filename or "img")[-1] or ".jpg"
    filename = f"{uuid_lib.uuid4().hex}{ext}"
    path = os.path.join(dest, filename)
    content = file.file.read()
    with open(path, "wb") as f:
        f.write(content)
    return f"/static/uploads/{sub}/{filename}"


def _require_store_owner(store: Store, user_id: str, is_superuser: bool) -> None:
    if is_superuser:
        return
    if str(store.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Bạn không phải chủ cửa hàng này")


# ─────────────────────────────────────────────────────────────
#  ProductCategory CRUD
# ─────────────────────────────────────────────────────────────

def list_categories(db: Session) -> list[ProductCategory]:
    return db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.sort_order).all()


def get_category(db: Session, cat_id: int) -> ProductCategory:
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại")
    return cat


def create_category(db: Session, data: CategoryCreate) -> ProductCategory:
    if db.query(ProductCategory).filter(ProductCategory.slug == data.slug).first():
        raise HTTPException(status_code=409, detail="Slug đã tồn tại")
    cat = ProductCategory(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(db: Session, cat_id: int, data: CategoryUpdate) -> ProductCategory:
    cat = get_category(db, cat_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, cat_id: int) -> None:
    cat = get_category(db, cat_id)
    cat.is_active = False  # soft-delete
    db.commit()


# ─────────────────────────────────────────────────────────────
#  Store CRUD
# ─────────────────────────────────────────────────────────────

def list_stores(db: Session, place_id: str | None = None, active_only: bool = True) -> list[Store]:
    q = db.query(Store)
    if active_only:
        q = q.filter(Store.is_active == True)
    if place_id:
        from app.domains.culture.model import Place
        place = db.query(Place).filter(Place.place_id == place_id).first()
        if place and place.lat and place.lon:
            point = f"SRID=4326;POINT({place.lon} {place.lat})"
            q = q.filter(func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), 2000))
        else:
            return []
    return q.limit(50).all()


def get_store(db: Session, store_id: int) -> Store:
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Cửa hàng không tồn tại")
    return store


def create_store(db: Session, data: StoreCreate, owner_id: str) -> Store:
    store = Store(**data.model_dump(), owner_id=owner_id)
    if data.lat and data.lon:
        store.geom = f"SRID=4326;POINT({data.lon} {data.lat})"
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def update_store(db: Session, store_id: int, data: StoreUpdate, user_id: str, is_superuser: bool) -> Store:
    store = get_store(db, store_id)
    _require_store_owner(store, user_id, is_superuser)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(store, k, v)
    if data.lat and data.lon:
        store.geom = f"SRID=4326;POINT({data.lon} {data.lat})"
    store.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(store)
    return store


def delete_store(db: Session, store_id: int, user_id: str, is_superuser: bool) -> None:
    store = get_store(db, store_id)
    _require_store_owner(store, user_id, is_superuser)
    store.is_active = False  # soft-delete
    store.updated_at = datetime.now(timezone.utc)
    db.commit()


def upload_store_image(db: Session, store_id: int, file: UploadFile, user_id: str, is_superuser: bool) -> Store:
    store = get_store(db, store_id)
    _require_store_owner(store, user_id, is_superuser)
    store.image_url = _save_upload(file, sub="stores")
    store.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(store)
    return store


# ─────────────────────────────────────────────────────────────
#  Product CRUD
# ─────────────────────────────────────────────────────────────

def list_products(db: Session, store_id: int | None = None) -> list[dict]:
    if store_id:
        return get_products_by_store(db, store_id)
    rows = db.query(Product).filter(Product.is_active == True).limit(100).all()
    return [_product_to_dict(p) for p in rows]


def _product_to_dict(prod: Product, inv: Inventory | None = None) -> dict:
    return {
        "product_id": prod.product_id,
        "name": prod.name,
        "price": prod.price,
        "original_price": prod.original_price,
        "description": prod.description,
        "sku": prod.sku,
        "image_url": prod.image_url,
        "category_id": prod.category_id,
        "tags": prod.tags,
        "size": prod.size,
        "color": prod.color,
        "is_active": prod.is_active,
        "embedding_status": prod.embedding_status,
        "created_at": prod.created_at,
        "stock": inv.stock if inv else 0,
        "store_id": inv.store_id if inv else None,
        "store_price": inv.store_price if inv else None,
        "is_available": inv.is_available if inv else True,
    }


def get_product_by_id(db: Session, product_id: int):
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    return _product_to_dict(prod)


def get_products_by_store(db: Session, store_id: int) -> list[dict]:
    rows = (
        db.query(Product, Inventory)
        .join(Inventory, Product.product_id == Inventory.product_id)
        .filter(Inventory.store_id == store_id, Product.is_active == True)
        .limit(50)
        .all()
    )
    return [_product_to_dict(p, inv) for p, inv in rows]


def create_product(db: Session, data: ProductCreate) -> Product:
    prod = Product(**data.model_dump(), embedding_status="pending")
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    changed = data.model_dump(exclude_none=True)
    for k, v in changed.items():
        setattr(prod, k, v)
    # Re-trigger embedding if name/description changed
    if "name" in changed or "description" in changed:
        prod.embedding_status = "pending"
    prod.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prod)
    return prod


def delete_product(db: Session, product_id: int) -> None:
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    prod.is_active = False
    prod.updated_at = datetime.now(timezone.utc)
    db.commit()


def upload_product_image(db: Session, product_id: int, file: UploadFile) -> Product:
    prod = db.query(Product).filter(Product.product_id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    prod.image_url = _save_upload(file, sub="products")
    prod.embedding_status = "pending"  # re-embed with new image
    prod.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prod)
    return prod


# ─────────────────────────────────────────────────────────────
#  Inventory (store-product link) CRUD
# ─────────────────────────────────────────────────────────────

def upsert_inventory(db: Session, store_id: int, data: InventoryUpsert, user_id: str, is_superuser: bool) -> Inventory:
    store = get_store(db, store_id)
    _require_store_owner(store, user_id, is_superuser)
    inv = (
        db.query(Inventory)
        .filter(Inventory.store_id == store_id, Inventory.product_id == data.product_id)
        .first()
    )
    if inv:
        inv.stock = data.stock
        inv.store_price = data.store_price
        inv.is_available = data.is_available
    else:
        inv = Inventory(
            store_id=store_id,
            product_id=data.product_id,
            stock=data.stock,
            store_price=data.store_price,
            is_available=data.is_available,
        )
        db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def remove_inventory(db: Session, store_id: int, product_id: int, user_id: str, is_superuser: bool) -> None:
    store = get_store(db, store_id)
    _require_store_owner(store, user_id, is_superuser)
    inv = db.query(Inventory).filter(Inventory.store_id == store_id, Inventory.product_id == product_id).first()
    if inv:
        db.delete(inv)
        db.commit()


# ─────────────────────────────────────────────────────────────
#  Faceted Search
# ─────────────────────────────────────────────────────────────

def faceted_search(db: Session, f: SearchFacets) -> dict:
    keyword = f"%{f.q}%" if f.q else None

    # ── Stores (simple keyword match) ──
    store_q = db.query(Store).filter(Store.is_active == True)
    if keyword:
        store_q = store_q.filter(Store.name.ilike(keyword))
    if f.lat and f.lon:
        point = f"SRID=4326;POINT({f.lon} {f.lat})"
        store_q = store_q.filter(
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), f.radius)
        )
    stores = store_q.limit(10).all()

    # ── Products ──
    prod_q = (
        db.query(Product, Inventory, Store, ProductCategory)
        .join(Inventory, Product.product_id == Inventory.product_id, isouter=True)
        .join(Store, Inventory.store_id == Store.store_id, isouter=True)
        .join(ProductCategory, Product.category_id == ProductCategory.id, isouter=True)
        .filter(Product.is_active == True)
    )

    if keyword:
        prod_q = prod_q.filter(
            or_(Product.name.ilike(keyword), Product.tags.ilike(keyword))
        )
    if f.category_id:
        prod_q = prod_q.filter(Product.category_id == f.category_id)
    if f.min_price is not None:
        prod_q = prod_q.filter(
            func.coalesce(Inventory.store_price, Product.price) >= f.min_price
        )
    if f.max_price is not None:
        prod_q = prod_q.filter(
            func.coalesce(Inventory.store_price, Product.price) <= f.max_price
        )
    if f.in_stock_only:
        prod_q = prod_q.filter(Inventory.stock > Inventory.locked_stock, Inventory.is_available == True)
    if f.lat and f.lon:
        point = f"SRID=4326;POINT({f.lon} {f.lat})"
        prod_q = prod_q.filter(
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), f.radius)
        )

    total = prod_q.count()
    offset = (f.page - 1) * f.page_size

    # Sorting
    if f.sort == "price_asc":
        prod_q = prod_q.order_by(func.coalesce(Inventory.store_price, Product.price).asc())
    elif f.sort == "price_desc":
        prod_q = prod_q.order_by(func.coalesce(Inventory.store_price, Product.price).desc())

    rows = prod_q.offset(offset).limit(f.page_size).all()

    products = []
    for prod, inv, store, cat in rows:
        dist = None
        if f.lat and f.lon and store and store.lat and store.lon:
            dist = float(
                db.scalar(
                    func.ST_Distance(
                        func.ST_GeogFromText(f"SRID=4326;POINT({store.lon} {store.lat})"),
                        func.ST_GeogFromText(f"SRID=4326;POINT({f.lon} {f.lat})"),
                    )
                )
            )
        products.append({
            "product_id": prod.product_id,
            "name": prod.name,
            "price": inv.store_price if (inv and inv.store_price) else prod.price,
            "original_price": prod.original_price,
            "image_url": prod.image_url,
            "category_id": prod.category_id,
            "category_name": cat.name if cat else None,
            "tags": prod.tags,
            "store_id": store.store_id if store else None,
            "store_name": store.name if store else None,
            "stock": inv.stock if inv else 0,
            "is_available": inv.is_available if inv else True,
            "distance_m": round(dist, 1) if dist is not None else None,
        })

    if f.sort == "distance" and products:
        products.sort(key=lambda x: (x["distance_m"] is None, x["distance_m"] or 0))

    return {
        "stores": stores,
        "products": products,
        "total_products": total,
        "page": f.page,
        "page_size": f.page_size,
    }


# ─────────────────────────────────────────────────────────────
#  Legacy search (kept for backwards compat)
# ─────────────────────────────────────────────────────────────

def search_stores_and_products(db: Session, query: str) -> dict:
    keyword = f"%{query}%"
    stores = db.query(Store).filter(Store.name.ilike(keyword), Store.is_active == True).limit(10).all()
    rows = (
        db.query(Product, Inventory)
        .join(Inventory, Product.product_id == Inventory.product_id)
        .filter(Product.name.ilike(keyword), Product.is_active == True)
        .limit(20)
        .all()
    )
    products = [_product_to_dict(p, inv) for p, inv in rows]
    return {"stores": stores, "products": products}


def compare_product_prices(db: Session, product_id: int, current_store_id: int, lat=None, lon=None, radius=5000):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return []
    q = (
        db.query(Inventory, Store)
        .join(Store, Inventory.store_id == Store.store_id)
        .filter(Inventory.product_id == product_id, Inventory.stock > 0, Store.is_active == True)
    )
    if lat and lon:
        point = f"SRID=4326;POINT({lon} {lat})"
        q = q.filter(func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius))
    rows = q.limit(10).all()
    result = []
    for inv, store in rows:
        effective_price = inv.store_price if inv.store_price else product.price
        result.append({
            "store_id": store.store_id,
            "store_name": store.name,
            "address": store.address,
            "price": effective_price,
            "stock": inv.stock - inv.locked_stock,
            "is_current": store.store_id == current_store_id,
            "category": store.category,
        })
    result.sort(key=lambda x: (0 if x["is_current"] else 1, x["price"]))
    return result


# ─────────────────────────────────────────────────────────────
#  Inventory locks (unchanged logic)
# ─────────────────────────────────────────────────────────────

async def create_lock(db: Session, redis: Redis, request: LockRequest, user_id: int):
    from app.core.config import settings
    lock_key = f"lock:prod:{request.product_id}"
    is_locked = await redis.get(lock_key)
    if is_locked and str(is_locked) != str(user_id):
        raise HTTPException(status_code=409, detail="Sản phẩm này đang nằm trong giỏ của người khác!")
    inv = db.query(Inventory).filter(Inventory.product_id == request.product_id).with_for_update().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Sản phẩm không có tồn kho.")
    total_available = sum(
        max(0, i.stock - i.locked_stock)
        for i in db.query(Inventory).filter(Inventory.product_id == request.product_id).all()
    )
    if total_available < request.quantity:
        raise HTTPException(status_code=400, detail=f"Không đủ hàng. Còn: {total_available}")
    inv.locked_stock += request.quantity
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.INVENTORY_LOCK_TTL)
    new_lock = InventoryLock(product_id=inv.product_id, user_id=user_id, quantity=request.quantity, status="soft_locked", expires_at=expires_at)
    db.add(new_lock)
    db.flush()
    try:
        await redis.set(lock_key, user_id, ex=settings.INVENTORY_LOCK_TTL)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail="Hệ thống đang có sự cố.")
    db.commit()
    db.refresh(new_lock)
    return new_lock


async def get_user_locks_with_ttl(db: Session, redis: Redis, user_id: int):
    locks = db.query(InventoryLock).filter(InventoryLock.user_id == user_id, InventoryLock.status == "soft_locked").all()
    results = []
    for lock in locks:
        try:
            ttl = await redis.ttl(f"lock:prod:{lock.product_id}")
        except Exception:
            ttl = -1
        results.append({"id": lock.id, "product_id": lock.product_id, "quantity": lock.quantity, "status": lock.status, "expires_at": lock.expires_at, "ttl_seconds": max(ttl, 0)})
    return results


def check_and_release_expired_locks(db: Session) -> int:
    now = datetime.now(timezone.utc)
    expired = db.query(InventoryLock).filter(InventoryLock.status == "soft_locked", InventoryLock.expires_at <= now).with_for_update().all()
    count = 0
    for lock in expired:
        inv = db.query(Inventory).filter(Inventory.product_id == lock.product_id).first()
        if inv:
            inv.locked_stock = max(0, inv.locked_stock - lock.quantity)
        lock.status = "expired"
        count += 1
    db.commit()
    logger.info(f"[Sweep] Hoàn trả tồn kho cho {count} lock hết hạn")
    return count


# ─────────────────────────────────────────────────────────────
#  Order (unchanged logic)
# ─────────────────────────────────────────────────────────────

def _generate_order_code() -> str:
    return "AE" + "".join(random.choices(string.digits, k=6))


def _build_vietqr_url(amount: int, order_code: str) -> str:
    bank_id = "970422"
    account_no = "0123456789"
    info = urllib.parse.quote(f"AEGIS {order_code}")
    return f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={info}&accountName=AEGIS%20O2O"


async def finalize_order(db: Session, redis: Redis, data: OrderCreate, user_id: int):
    product = db.query(Product).filter(Product.product_id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    total_amount = int(product.price * data.quantity)
    order_code = _generate_order_code()
    lock_key = f"lock:prod:{data.product_id}"
    try:
        await redis.delete(lock_key)
    except Exception:
        pass
    inv_q = db.query(Inventory).filter(Inventory.product_id == data.product_id)
    if data.store_id:
        inv_q = inv_q.filter(Inventory.store_id == data.store_id)
    inv = inv_q.with_for_update().first()
    if inv:
        inv.stock = max(0, inv.stock - data.quantity)
        inv.locked_stock = max(0, inv.locked_stock - data.quantity)
    existing_lock = db.query(InventoryLock).filter(InventoryLock.product_id == data.product_id, InventoryLock.user_id == user_id, InventoryLock.status == "soft_locked").first()
    if existing_lock:
        existing_lock.status = "completed"
    new_order = Order(user_id=user_id, product_id=data.product_id, store_id=data.store_id, quantity=data.quantity, total_amount=total_amount, full_name=data.full_name, phone=data.phone, address=data.address, status="PENDING_SHIP", order_code=order_code)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return {"order_id": new_order.order_id, "order_code": new_order.order_code, "status": new_order.status, "total_amount": total_amount, "product_name": product.name, "vietqr_url": _build_vietqr_url(total_amount, order_code)}
