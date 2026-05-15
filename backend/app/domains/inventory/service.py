from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.domains.inventory.model import Product, InventoryLock, Store, Inventory, Order
from app.domains.inventory.schema import LockRequest, OrderCreate
from redis.asyncio import Redis
from datetime import datetime, timezone
import logging
import random
import string
import urllib.parse

logger = logging.getLogger(__name__)


PRODUCT_IMAGE_FALLBACKS = {
    "giày": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80",
    "sneaker": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80",
    "áo": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=700&q=80",
    "quần": "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=700&q=80",
    "balo": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=700&q=80",
    "nước hoa": "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=700&q=80",
    "kính": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=700&q=80",
    "mũ": "https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&w=700&q=80",
    "cà phê": "https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=700&q=80",
    "vòng": "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?auto=format&fit=crop&w=700&q=80",
}


def _product_image_url(product: Product) -> str | None:
    if product.image_url and "via.placeholder.com" not in product.image_url:
        return product.image_url

    name = (product.name or "").lower()
    for keyword, image_url in PRODUCT_IMAGE_FALLBACKS.items():
        if keyword in name:
            return image_url
    return "https://images.unsplash.com/photo-1492724441997-5dc865305da7?auto=format&fit=crop&w=700&q=80"


def _lock_key(product_id: int, store_id: int | None = None) -> str:
    store_part = store_id if store_id is not None else "any"
    return f"lock:store:{store_part}:prod:{product_id}"


def _available_stock(inv: Inventory) -> int:
    return max(0, inv.stock - inv.locked_stock)


def reconcile_inventory_locks(db: Session) -> None:
    now = datetime.now(timezone.utc)
    inventories = db.query(Inventory).all()
    inventory_by_key = {(inv.product_id, inv.store_id): inv for inv in inventories}

    for inv in inventories:
        inv.locked_stock = 0

    active_locks = db.query(InventoryLock).filter(
        InventoryLock.status == "soft_locked",
        InventoryLock.expires_at > now,
    ).all()

    for lock in active_locks:
        inv = inventory_by_key.get((lock.product_id, lock.store_id))
        if inv is None and lock.store_id is None:
            inv = db.query(Inventory).filter(Inventory.product_id == lock.product_id).first()
            if inv:
                lock.store_id = inv.store_id
        if inv:
            inv.locked_stock = min(inv.stock, inv.locked_stock + lock.quantity)

    db.flush()


def sweep_and_reconcile_inventory(db: Session) -> None:
    check_and_release_expired_locks(db, commit=False)
    reconcile_inventory_locks(db)
    db.commit()


def get_all_stores(db: Session, place_id: str | None = None):
    from sqlalchemy import func
    from app.domains.culture.model import Place

    query = db.query(Store).filter(Store.category == 'shopping')
    if place_id:
        place = db.query(Place).filter(Place.place_id == place_id).first()
        if place and place.lat and place.lon:
            point = f"SRID=4326;POINT({place.lon} {place.lat})"
            query = query.filter(func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), 2000))
        else:
            return []
            
    return query.limit(20).all()

def get_product_by_id(db: Session, product_id: int):
    return db.query(Product).filter(Product.product_id == product_id).first()


def get_products_by_store(db: Session, store_id: int):
    sweep_and_reconcile_inventory(db)
    # Join Inventory and Product to get real stock and store_id
    results = db.query(Product, Inventory).join(
        Inventory, Product.product_id == Inventory.product_id
    ).filter(Inventory.store_id == store_id).limit(50).all()
    
    products = []
    for prod, inv in results:
        prod_dict = {
            "product_id": prod.product_id,
            "name": prod.name,
            "price": prod.price,
            "original_price": prod.original_price,
            "description": prod.description,
            "image_url": _product_image_url(prod),
            "stock": _available_stock(inv),
            "store_id": inv.store_id
        }
        products.append(prod_dict)
    
    return products


def search_stores_and_products(db: Session, query: str):
    sweep_and_reconcile_inventory(db)
    """
    Tìm kiếm tổng hợp: Tìm Store hoặc Product theo keyword (ILIKE).
    Trả về dict { stores: [...], products: [...] }.
    """
    keyword = f"%{query}%"
    
    stores = db.query(Store).filter(
        Store.name.ilike(keyword)
    ).limit(10).all()
    
    # Tìm product qua tên hoặc description
    product_rows = db.query(Product, Inventory).join(
        Inventory, Product.product_id == Inventory.product_id
    ).filter(
        Product.name.ilike(keyword)
    ).limit(20).all()
    
    products = []
    for prod, inv in product_rows:
        products.append({
            "product_id": prod.product_id,
            "name": prod.name,
            "price": prod.price,
            "original_price": prod.original_price,
            "description": prod.description,
            "image_url": _product_image_url(prod),
            "stock": _available_stock(inv),
            "store_id": inv.store_id,
        })
    
    return {"stores": stores, "products": products}


def compare_product_prices(db: Session, product_id: int, current_store_id: int, lat: float = None, lon: float = None, radius: int = 5000):
    """
    So sánh giá sản phẩm tại cửa hàng hiện tại vs các cửa hàng khác trong bán kính.
    Trả về list[dict] gồm store info + price + stock.
    """
    from sqlalchemy import func
    
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return []

    # Tìm tất cả stores bán sản phẩm này
    query = db.query(Inventory, Store).join(
        Store, Inventory.store_id == Store.store_id
    ).filter(
        Inventory.product_id == product_id,
        Inventory.stock > 0,
    )
    
    # Filter theo bán kính nếu có tọa độ
    if lat and lon:
        point = f"SRID=4326;POINT({lon} {lat})"
        query = query.filter(
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius)
        )
    
    rows = query.limit(10).all()
    
    comparisons = []
    for inv, store in rows:
        comparisons.append({
            "store_id": store.store_id,
            "store_name": store.name,
            "address": store.address,
            "price": product.price,
            "stock": _available_stock(inv),
            "is_current": store.store_id == current_store_id,
            "category": store.category,
        })
    
    # Sort: current store first, then by price ascending
    comparisons.sort(key=lambda x: (0 if x["is_current"] else 1, x["price"]))
    
    return comparisons


async def create_lock(db: Session, redis: Redis, request: LockRequest, user_id):
    from app.core.config import settings
    sweep_and_reconcile_inventory(db)
    user_id_str = str(user_id)

    # === PHASE 1: REDIS GATE ===
    lock_key = _lock_key(request.product_id, request.store_id)
    is_locked = await redis.get(lock_key)
    locked_by = is_locked.decode() if isinstance(is_locked, bytes) else is_locked
    if locked_by and str(locked_by) != user_id_str:
        raise HTTPException(
            status_code=409,
            detail="Sản phẩm này đang nằm trong giỏ của người khác! Vui lòng thử lại sau."
        )

    # === PHASE 2: POSTGRES ROW LOCK (Qua bảng Inventory) ===
    # Lấy thông tin Tồn kho của Product (DBeaver tách riêng bảng)
    inv_query = db.query(Inventory).filter(Inventory.product_id == request.product_id)
    if request.store_id:
        inv_query = inv_query.filter(Inventory.store_id == request.store_id)
    inv = inv_query.with_for_update().first()

    if not inv:
        raise HTTPException(status_code=404, detail="Sản phẩm không có thông tin tồn kho hoặc đã hết.")

    # Lấy TỔNG tồn kho có sẵn từ TẤT CẢ Store có bán product này
    # (1 product có thể được bán tại nhiều store trong travel_app)
    if request.store_id:
        total_available = max(0, inv.stock - inv.locked_stock)
    else:
        total_available = sum(max(0, i.stock - i.locked_stock) for i in db.query(Inventory).filter(
            Inventory.product_id == request.product_id
        ).all())
    if total_available < request.quantity:
        raise HTTPException(status_code=400, detail=f"Không đủ hàng. Tồn kho còn: {total_available}")

    # Chuẩn bị ghi DB - trừ từ inventory record đầu tiên còn hàng
    inv.locked_stock += request.quantity
    new_lock = InventoryLock(
        product_id=inv.product_id,
        store_id=inv.store_id,
        user_id=user_id,
        quantity=request.quantity,
        status="soft_locked"
    )
    db.add(new_lock)
    db.flush()

    # === PHASE 3: SET REDIS TTL ===
    try:
        await redis.set(lock_key, user_id_str, ex=settings.INVENTORY_LOCK_TTL)
    except Exception as redis_error:
        db.rollback()
        logger.error(f"Redis SET thất bại cho lock_key={lock_key}: {redis_error}")
        raise HTTPException(
            status_code=503,
            detail="Hệ thống đang có sự cố. Vui lòng thử lại."
        )

    # === PHASE 4: COMMIT ===
    db.commit()
    db.refresh(new_lock)
    return new_lock


async def get_user_locks_with_ttl(db: Session, redis: Redis, user_id):
    sweep_and_reconcile_inventory(db)
    locks = db.query(InventoryLock).filter(
        InventoryLock.user_id == user_id,
        InventoryLock.status == "soft_locked"
    ).all()
    results = []
    for lock in locks:
        product = db.query(Product).filter(Product.product_id == lock.product_id).first()
        inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
        if lock.store_id:
            inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
        inv = inv_query.first()
        try:
            ttl = await redis.ttl(_lock_key(lock.product_id, lock.store_id))
        except Exception:
            ttl = -1
        if ttl >= 0:
            ttl_seconds = ttl
        else:
            ttl_seconds = max(
                0,
                int((lock.expires_at - datetime.now(timezone.utc)).total_seconds())
            )
        results.append({
            "id": lock.id,
            "product_id": lock.product_id,
            "product_name": product.name if product else None,
            "product_price": product.price if product else None,
            "product_image_url": _product_image_url(product) if product else None,
            "store_id": lock.store_id or (inv.store_id if inv else None),
            "quantity": lock.quantity,
            "status": lock.status,
            "expires_at": lock.expires_at,
            "ttl_seconds": ttl_seconds
        })
    return results


async def cancel_lock(db: Session, redis: Redis, lock_id: int, user_id):
    lock = db.query(InventoryLock).filter(
        InventoryLock.id == lock_id,
        InventoryLock.user_id == user_id,
        InventoryLock.status == "soft_locked"
    ).with_for_update().first()

    if not lock:
        raise HTTPException(status_code=404, detail="Lock không tồn tại hoặc đã hết hiệu lực.")

    inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
    if lock.store_id:
        inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
    inv = inv_query.with_for_update().first()
    if inv:
        inv.locked_stock = max(0, inv.locked_stock - lock.quantity)

    lock.status = "cancelled"
    try:
        await redis.delete(_lock_key(lock.product_id, lock.store_id))
        await redis.delete(f"lock:prod:{lock.product_id}")
    except Exception:
        pass

    db.commit()
    return {"message": "Đã hủy giữ hàng.", "lock_id": lock.id}


def check_and_release_expired_locks(db: Session, commit: bool = True) -> int:
    now = datetime.now(timezone.utc)
    expired_locks = db.query(InventoryLock).filter(
        InventoryLock.status == "soft_locked",
        InventoryLock.expires_at <= now
    ).with_for_update().all()

    released_count = 0
    for lock in expired_locks:
        inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
        if lock.store_id:
            inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
        inv = inv_query.first()
        if inv:
            inv.locked_stock = max(0, inv.locked_stock - lock.quantity)
        lock.status = "expired"
        released_count += 1

    if commit:
        reconcile_inventory_locks(db)
        db.commit()
    logger.info(f"[Sweep] Đã hoàn trả tồn kho cho {released_count} lock hết hạn")
    return released_count


def _generate_order_code() -> str:
    """Sinh mã đơn hàng 8 ký tự: AE + 6 chữ số ngẫu nhiên"""
    return "AE" + "".join(random.choices(string.digits, k=6))


def _build_vietqr_url(amount: int, order_code: str) -> str:
    """Sinh URL ảnh VietQR chuẩn ngân hàng Việt Nam."""
    bank_id = "970422"       # MB Bank (ví dụ)
    account_no = "0123456789"  # Tài khoản demo
    template = "compact2"
    info = urllib.parse.quote(f"AEGIS {order_code}")
    return f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={info}&accountName=AEGIS%20O2O"


async def finalize_order(db: Session, redis: Redis, data: OrderCreate, user_id):
    """
    Hoàn tất đơn hàng O2O:
    1. Tìm product, tính tổng tiền
    2. Xóa Redis lock (nếu có)
    3. Trừ tồn kho vĩnh viễn trong PostgreSQL
    4. Tạo Order record với trạng thái PENDING_SHIP
    """
    product = db.query(Product).filter(Product.product_id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

    total_amount = int(product.price * data.quantity)
    order_code = _generate_order_code()

    # Xóa Redis lock
    lock_key = _lock_key(data.product_id, data.store_id)
    try:
        await redis.delete(lock_key)
        await redis.delete(f"lock:prod:{data.product_id}")
    except Exception:
        pass  # Non-critical

    # Trừ tồn kho vĩnh viễn
    inv_query = db.query(Inventory).filter(Inventory.product_id == data.product_id)
    if data.store_id:
        inv_query = inv_query.filter(Inventory.store_id == data.store_id)
    inv = inv_query.with_for_update().first()
    
    if inv:
        inv.stock = max(0, inv.stock - data.quantity)
        inv.locked_stock = max(0, inv.locked_stock - data.quantity)
    
    # Đánh dấu lock cũ là completed
    existing_lock = db.query(InventoryLock).filter(
        InventoryLock.product_id == data.product_id,
        InventoryLock.store_id == data.store_id,
        InventoryLock.user_id == user_id,
        InventoryLock.status == "soft_locked"
    ).first()
    if existing_lock:
        existing_lock.status = "completed"

    # Tạo Order
    new_order = Order(
        user_id=user_id,
        product_id=data.product_id,
        store_id=data.store_id,
        quantity=data.quantity,
        total_amount=total_amount,
        full_name=data.full_name,
        phone=data.phone,
        address=data.address,
        status="PENDING_SHIP",
        order_code=order_code,
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    vietqr_url = _build_vietqr_url(total_amount, order_code)

    return {
        "order_id": new_order.order_id,
        "order_code": new_order.order_code,
        "status": new_order.status,
        "total_amount": total_amount,
        "product_name": product.name,
        "vietqr_url": vietqr_url,
    }
