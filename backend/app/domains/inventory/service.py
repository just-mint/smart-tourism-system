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
    # Join Inventory and Product to get real stock and store_id
    results = db.query(Product, Inventory).join(
        Inventory, Product.product_id == Inventory.product_id
    ).filter(Inventory.store_id == store_id).limit(50).all()
    
    products = []
    for prod, inv in results:
        prod_dict = {
            "product_id": prod.product_id,
            "name": prod.name,
            "price": inv.price_override if inv.price_override is not None else prod.price,
            "original_price": prod.original_price,
            "description": prod.description,
            "image_url": prod.image_url,
            "stock": inv.stock,
            "store_id": inv.store_id
        }
        products.append(prod_dict)
    
    return products


def search_stores_and_products(db: Session, query: str):
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
            "price": inv.price_override if inv.price_override is not None else prod.price,
            "original_price": prod.original_price,
            "description": prod.description,
            "image_url": prod.image_url,
            "stock": inv.stock,
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
            "price": inv.price_override if inv.price_override is not None else product.price,
            "stock": inv.stock - inv.locked_stock,
            "is_current": store.store_id == current_store_id,
            "category": store.category,
        })
    
    # Sort: current store first, then by price ascending
    comparisons.sort(key=lambda x: (0 if x["is_current"] else 1, x["price"]))
    
    return comparisons


async def create_lock(db: Session, redis: Redis, request: LockRequest, user_id: int):
    from app.core.config import settings
    if not getattr(request, "store_id", None):
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp store_id để khóa hàng cho cửa hàng cụ thể.")
    lock_key = f"lock:prod:{request.product_id}:store:{request.store_id}"

    # === PHASE 1: REDIS GATE ===
    is_locked = await redis.get(lock_key)
    if is_locked and str(is_locked) != str(user_id):
        raise HTTPException(
            status_code=409,
            detail="Sản phẩm này đang nằm trong giỏ của người khác! Vui lòng thử lại sau."
        )

    # === PHASE 2: POSTGRES ROW LOCK (Qua bảng Inventory) ===
    # Lấy thông tin Tồn kho của Product (DBeaver tách riêng bảng)
    inv = db.query(Inventory).filter(
        Inventory.product_id == request.product_id,
        Inventory.store_id == request.store_id,
    ).with_for_update().first()

    if not inv:
        raise HTTPException(status_code=404, detail="Sản phẩm không có thông tin tồn kho hoặc đã hết.")

    # Kiểm tra tồn kho tại cửa hàng cụ thể
    if not inv:
        raise HTTPException(status_code=404, detail="Sản phẩm không có thông tin tồn kho tại cửa hàng này hoặc đã hết.")
    available = max(0, inv.stock - inv.locked_stock)
    if available < request.quantity:
        raise HTTPException(status_code=400, detail=f"Không đủ hàng tại cửa hàng. Tồn kho còn: {available}")

    # Chuẩn bị ghi DB - trừ từ inventory record đầu tiên còn hàng
    inv.locked_stock += request.quantity
    new_lock = InventoryLock(
        product_id=inv.product_id,
        store_id=request.store_id,
        user_id=user_id,
        quantity=request.quantity,
        status="soft_locked"
    )
    db.add(new_lock)
    db.flush()

    # === PHASE 3: SET REDIS TTL ===
    try:
        await redis.set(lock_key, user_id, ex=settings.INVENTORY_LOCK_TTL)
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


async def get_user_locks_with_ttl(db: Session, redis: Redis, user_id: int):
    locks = db.query(InventoryLock).filter(
        InventoryLock.user_id == user_id,
        InventoryLock.status == "soft_locked"
    ).all()
    results = []
    for lock in locks:
        try:
            ttl = await redis.ttl(f"lock:prod:{lock.product_id}:store:{getattr(lock, 'store_id', '')}")
        except Exception:
            ttl = -1
        results.append({
            "id": lock.id,
            "product_id": lock.product_id,
            "store_id": getattr(lock, "store_id", None),
            "quantity": lock.quantity,
            "status": lock.status,
            "expires_at": lock.expires_at,
            "ttl_seconds": max(ttl, 0)
        })
    return results


def check_and_release_expired_locks(db: Session) -> int:
    now = datetime.now(timezone.utc)
    expired_locks = db.query(InventoryLock).filter(
        InventoryLock.status == "soft_locked",
        InventoryLock.expires_at <= now
    ).with_for_update().all()

    released_count = 0
    for lock in expired_locks:
        inv = db.query(Inventory).filter(
            Inventory.product_id == lock.product_id,
            Inventory.store_id == getattr(lock, "store_id", None),
        ).first()
        if inv:
            inv.locked_stock = max(0, inv.locked_stock - lock.quantity)
        lock.status = "expired"
        released_count += 1

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


async def finalize_order(db: Session, redis: Redis, data: OrderCreate, user_id: int):
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

    # total_amount sẽ được tính lại dựa trên giá (có thể bị override) sau khi xác định store_id từ lock

    # Yêu cầu phải có lock_id kèm theo
    if not getattr(data, "lock_id", None):
        raise HTTPException(status_code=400, detail="Phải cung cấp lock_id khi tạo đơn hàng.")

    lock = db.query(InventoryLock).filter(InventoryLock.id == data.lock_id).first()
    if not lock or lock.user_id != user_id or lock.status != "soft_locked":
        raise HTTPException(status_code=400, detail="Lock không hợp lệ hoặc đã hết hạn.")
    if lock.product_id != data.product_id or lock.quantity != data.quantity:
        raise HTTPException(status_code=400, detail="Thông tin lock không khớp với đơn hàng.")

    # Xóa Redis lock (per-store key)
    lock_key = f"lock:prod:{data.product_id}:store:{lock.store_id}"
    try:
        await redis.delete(lock_key)
    except Exception:
        pass  # Non-critical

    # Trừ tồn kho vĩnh viễn
    # Trừ tồn kho vĩnh viễn tại cửa hàng được lock
    inv = db.query(Inventory).filter(
        Inventory.product_id == data.product_id,
        Inventory.store_id == lock.store_id,
    ).with_for_update().first()

    if inv:
        inv.stock = max(0, inv.stock - data.quantity)
        inv.locked_stock = max(0, inv.locked_stock - data.quantity)
        unit_price = inv.price_override if inv.price_override is not None else product.price
    else:
        unit_price = product.price

    total_amount = int(unit_price * data.quantity)

    # Retry loop to generate unique order_code
    for _ in range(5):
        order_code = _generate_order_code()
        if not db.query(Order).filter(Order.order_code == order_code).first():
            break
    else:
        raise HTTPException(status_code=500, detail="Hệ thống bận, không thể tạo mã đơn hàng. Vui lòng thử lại.")

    # Đánh dấu lock là completed
    lock.status = "completed"

    # Tạo Order
    new_order = Order(
        user_id=user_id,
        product_id=data.product_id,
        store_id=lock.store_id,
        quantity=data.quantity,
        total_amount=total_amount,
        full_name=data.full_name,
        phone=data.phone,
        address=data.address,
        status="AWAITING_PAYMENT",
        order_code=order_code,
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Trả về mock payment URL (chờ thanh toán)
    mock_payment_url = f"https://mock-pay.local/pay/{order_code}"

    return {
        "order_id": new_order.order_id,
        "order_code": new_order.order_code,
        "status": new_order.status,
        "total_amount": total_amount,
        "product_name": product.name,
        "vietqr_url": mock_payment_url,
    }
