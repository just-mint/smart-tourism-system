import hashlib
import hmac
import logging
import random
import string
import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.inventory.model import (
    Inventory,
    InventoryEvent,
    InventoryLock,
    Order,
    Payment,
    Product,
    Store,
)
from app.domains.inventory.schema import LockRequest, OrderCreate, PaymentWebhook

logger = logging.getLogger(__name__)


def _lock_key(lock_id: int) -> str:
    return f"inventory_lock:{lock_id}"


def _log_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | int,
    action: str,
    user_id=None,
    payload: dict | None = None,
) -> None:
    db.add(
        InventoryEvent(
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            action=action,
            payload=payload or {},
        )
    )


def get_all_stores(db: Session, place_id: str | None = None):
    from sqlalchemy import func

    from app.domains.culture.model import Place

    query = db.query(Store)
    if place_id:
        place = db.query(Place).filter(Place.place_id == place_id).first()
        if place and place.lat and place.lon:
            point = f"SRID=4326;POINT({place.lon} {place.lat})"
            query = query.filter(
                func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), 2000)
            )
        else:
            return []

    return query.limit(20).all()


def get_product_by_id(db: Session, product_id: int):
    return db.query(Product).filter(Product.product_id == product_id).first()


def get_products_by_store(db: Session, store_id: int):
    # Join Inventory and Product to get real stock and store_id
    results = (
        db.query(Product, Inventory)
        .join(Inventory, Product.product_id == Inventory.product_id)
        .filter(Inventory.store_id == store_id)
        .limit(50)
        .all()
    )

    products = []
    for prod, inv in results:
        available_stock = max(0, inv.stock - inv.locked_stock)
        if available_stock <= 0:
            continue

        prod_dict = {
            "product_id": prod.product_id,
            "name": prod.name,
            "price": inv.price_override
            if inv.price_override is not None
            else prod.price,
            "original_price": prod.original_price,
            "description": prod.description,
            "image_url": prod.image_url,
            "stock": available_stock,
            "store_id": inv.store_id,
        }
        products.append(prod_dict)

    return products


def search_stores_and_products(db: Session, query: str):
    """
    Tìm kiếm tổng hợp: Tìm Store hoặc Product theo keyword (ILIKE).
    Trả về dict { stores: [...], products: [...] }.
    """
    keyword = f"%{query}%"

    stores = db.query(Store).filter(Store.name.ilike(keyword)).limit(10).all()

    # Tìm product qua tên hoặc description
    product_rows = (
        db.query(Product, Inventory)
        .join(Inventory, Product.product_id == Inventory.product_id)
        .filter(Product.name.ilike(keyword))
        .limit(20)
        .all()
    )

    products = []
    for prod, inv in product_rows:
        available_stock = max(0, inv.stock - inv.locked_stock)
        if available_stock <= 0:
            continue

        products.append(
            {
                "product_id": prod.product_id,
                "name": prod.name,
                "price": inv.price_override
                if inv.price_override is not None
                else prod.price,
                "original_price": prod.original_price,
                "description": prod.description,
                "image_url": prod.image_url,
                "stock": available_stock,
                "store_id": inv.store_id,
            }
        )

    return {"stores": stores, "products": products}


def compare_product_prices(
    db: Session,
    product_id: int,
    current_store_id: int,
    lat: float = None,
    lon: float = None,
    radius: int = 5000,
):
    """
    So sánh giá sản phẩm tại cửa hàng hiện tại vs các cửa hàng khác trong bán kính.
    Trả về list[dict] gồm store info + price + stock.
    """
    from sqlalchemy import func

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return []

    # Tìm tất cả stores bán sản phẩm này
    query = (
        db.query(Inventory, Store)
        .join(Store, Inventory.store_id == Store.store_id)
        .filter(
            Inventory.product_id == product_id,
            Inventory.stock > Inventory.locked_stock,
        )
    )

    # Filter theo bán kính nếu có tọa độ
    if lat is not None and lon is not None:
        point = f"SRID=4326;POINT({lon} {lat})"
        query = query.filter(
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius)
        )

    rows = query.limit(10).all()

    comparisons = []
    for inv, store in rows:
        comparisons.append(
            {
                "store_id": store.store_id,
                "store_name": store.name,
                "address": store.address,
                "price": inv.price_override
                if inv.price_override is not None
                else product.price,
                "stock": max(0, inv.stock - inv.locked_stock),
                "is_current": store.store_id == current_store_id,
                "category": store.category,
            }
        )

    # Sort: current store first, then by price ascending
    comparisons.sort(key=lambda x: (0 if x["is_current"] else 1, x["price"]))

    return comparisons


async def create_lock(db: Session, redis: Redis, request: LockRequest, user_id):
    if not getattr(request, "store_id", None):
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp store_id để khóa hàng cho cửa hàng cụ thể.",
        )

    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == request.product_id,
            Inventory.store_id == request.store_id,
        )
        .with_for_update()
        .first()
    )

    if not inv:
        raise HTTPException(
            status_code=404, detail="Sản phẩm không có thông tin tồn kho hoặc đã hết."
        )

    available = inv.stock - inv.locked_stock
    if available < request.quantity:
        raise HTTPException(
            status_code=409, detail=f"Không đủ hàng. Tồn kho còn: {available}"
        )

    inv.locked_stock += request.quantity
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.INVENTORY_LOCK_TTL
    )
    new_lock = InventoryLock(
        product_id=inv.product_id,
        store_id=inv.store_id,
        user_id=user_id,
        quantity=request.quantity,
        status="soft_locked",
        expires_at=expires_at,
    )
    try:
        db.add(new_lock)
        db.flush()
        _log_event(
            db,
            entity_type="inventory_lock",
            entity_id=new_lock.id,
            action="created",
            user_id=user_id,
            payload={
                "product_id": inv.product_id,
                "store_id": inv.store_id,
                "quantity": request.quantity,
                "expires_at": expires_at.isoformat(),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Tạo DB lock thất bại, đã rollback")
        raise

    db.refresh(new_lock)
    try:
        await redis.set(
            _lock_key(new_lock.id),
            str(user_id),
            ex=settings.INVENTORY_LOCK_TTL,
        )
    except Exception:
        logger.warning(
            "Không thể ghi Redis TTL cho lock_id=%s", new_lock.id, exc_info=True
        )
    return new_lock


async def get_user_locks_with_ttl(db: Session, redis: Redis, user_id):
    locks = (
        db.query(InventoryLock, Product, Store, Inventory)
        .join(Product, InventoryLock.product_id == Product.product_id)
        .join(Store, InventoryLock.store_id == Store.store_id)
        .join(
            Inventory,
            (InventoryLock.product_id == Inventory.product_id)
            & (InventoryLock.store_id == Inventory.store_id),
        )
        .filter(InventoryLock.user_id == user_id, InventoryLock.status == "soft_locked")
        .all()
    )
    results = []
    for lock, product, store, inv in locks:
        try:
            ttl = await redis.ttl(_lock_key(lock.id))
        except Exception:
            ttl = -1
        db_remaining = int(
            (lock.expires_at - datetime.now(timezone.utc)).total_seconds()
        )
        ttl_seconds = max(ttl if ttl >= 0 else db_remaining, 0)
        results.append(
            {
                "id": lock.id,
                "product_id": lock.product_id,
                "store_id": lock.store_id,
                "quantity": lock.quantity,
                "status": lock.status,
                "expires_at": lock.expires_at,
                "ttl_seconds": ttl_seconds,
                "product_name": product.name,
                "store_name": store.name,
                "unit_price": inv.price_override
                if inv.price_override is not None
                else product.price,
                "image_url": product.image_url,
            }
        )
    return results


async def cancel_lock(db: Session, redis: Redis, lock_id: int, user_id) -> None:
    lock = (
        db.query(InventoryLock)
        .filter(
            InventoryLock.id == lock_id,
            InventoryLock.user_id == user_id,
            InventoryLock.status == "soft_locked",
        )
        .with_for_update()
        .first()
    )
    if not lock:
        raise HTTPException(status_code=404, detail="Không tìm thấy lock còn hiệu lực.")

    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == lock.product_id,
            Inventory.store_id == lock.store_id,
        )
        .with_for_update()
        .first()
    )
    if inv:
        if inv.locked_stock < lock.quantity:
            raise HTTPException(
                status_code=409, detail="Dữ liệu giữ hàng không nhất quán."
            )
        inv.locked_stock -= lock.quantity
    lock.status = "cancelled"
    _log_event(
        db,
        entity_type="inventory_lock",
        entity_id=lock.id,
        action="cancelled",
        user_id=user_id,
        payload={
            "product_id": lock.product_id,
            "store_id": lock.store_id,
            "quantity": lock.quantity,
        },
    )
    db.commit()
    try:
        await redis.delete(_lock_key(lock.id))
    except Exception:
        logger.warning("Không thể xóa Redis key cho lock_id=%s", lock.id, exc_info=True)


def check_and_release_expired_locks(db: Session) -> int:
    now = datetime.now(timezone.utc)
    expired_locks = (
        db.query(InventoryLock)
        .filter(
            InventoryLock.status.in_(["soft_locked", "checkout_pending"]),
            InventoryLock.expires_at <= now,
        )
        .with_for_update()
        .all()
    )

    released_count = 0
    for lock in expired_locks:
        inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
        if lock.store_id is not None:
            inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
        inv = inv_query.with_for_update().first()
        if inv:
            inv.locked_stock = max(0, inv.locked_stock - lock.quantity)
        if lock.status == "checkout_pending":
            db.query(Order).filter(
                Order.lock_id == lock.id,
                Order.status == "PENDING_PAYMENT",
            ).update({"status": "EXPIRED"})
        lock.status = "expired"
        released_count += 1

    db.commit()
    logger.info(f"[Sweep] Đã hoàn trả tồn kho cho {released_count} lock hết hạn")
    return released_count


def _generate_order_code() -> str:
    """Sinh mã đơn hàng đủ entropy nhưng vẫn ngắn gọn."""
    timestamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AE{timestamp}{suffix}"


def _build_vietqr_url(amount: int, order_code: str) -> str:
    """Sinh URL ảnh VietQR chuẩn ngân hàng Việt Nam."""
    bank_id = settings.VIETQR_BANK_ID
    account_no = settings.VIETQR_ACCOUNT_NO
    template = settings.VIETQR_TEMPLATE
    account_name = urllib.parse.quote(settings.VIETQR_ACCOUNT_NAME)
    info = urllib.parse.quote(f"AEGIS {order_code}")
    return f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={info}&accountName={account_name}"


async def finalize_order(db: Session, redis: Redis, data: OrderCreate, user_id):
    """
    Hoàn tất đơn hàng O2O:
    1. Tìm product, tính tổng tiền
    2. Đổi lock sang checkout_pending, giữ locked_stock tới khi payment webhook về.
    3. Tạo Order record với trạng thái PENDING_PAYMENT.
    """
    product = db.query(Product).filter(Product.product_id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

    # total_amount sẽ được tính lại dựa trên giá (có thể bị override) sau khi xác định store_id từ lock

    # Yêu cầu phải có lock_id kèm theo
    if not getattr(data, "lock_id", None):
        raise HTTPException(
            status_code=400, detail="Phải cung cấp lock_id khi tạo đơn hàng."
        )

    lock = (
        db.query(InventoryLock)
        .filter(InventoryLock.id == data.lock_id)
        .with_for_update()
        .first()
    )
    if not lock or lock.user_id != user_id or lock.status != "soft_locked":
        raise HTTPException(
            status_code=400, detail="Lock không hợp lệ hoặc đã hết hạn."
        )
    if lock.expires_at <= datetime.now(timezone.utc):
        inv = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == lock.product_id,
                Inventory.store_id == lock.store_id,
            )
            .with_for_update()
            .first()
        )
        if inv and inv.locked_stock >= lock.quantity:
            inv.locked_stock -= lock.quantity
        lock.status = "expired"
        db.commit()
        try:
            await redis.delete(_lock_key(lock.id))
        except Exception:
            logger.warning(
                "Không thể xóa Redis key cho expired lock_id=%s", lock.id, exc_info=True
            )
        raise HTTPException(
            status_code=409, detail="Lock đã hết hạn. Vui lòng giữ hàng lại."
        )
    if lock.product_id != data.product_id or lock.quantity != data.quantity:
        raise HTTPException(
            status_code=400, detail="Thông tin lock không khớp với đơn hàng."
        )
    if lock.store_id != data.store_id:
        raise HTTPException(status_code=400, detail="Cửa hàng không khớp với lock.")

    order_store_id = lock.store_id

    # Kiểm tra tồn kho tại cửa hàng được lock. Chưa trừ stock ở bước này.
    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == data.product_id,
            Inventory.store_id == order_store_id,
        )
        .with_for_update()
        .first()
    )

    if inv:
        if inv.stock < data.quantity:
            raise HTTPException(
                status_code=400, detail="Tồn kho không còn đủ để tạo đơn."
            )
        if inv.locked_stock < data.quantity:
            raise HTTPException(
                status_code=409, detail="Số lượng giữ hàng không hợp lệ."
            )
        unit_price = (
            inv.price_override if inv.price_override is not None else product.price
        )
    else:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tồn kho cho sản phẩm đã giữ."
        )

    total_amount = int(unit_price * data.quantity)

    for _ in range(5):
        order_code = _generate_order_code()
        if not db.query(Order).filter(Order.order_code == order_code).first():
            break
    else:
        raise HTTPException(
            status_code=500,
            detail="Hệ thống bận, không thể tạo mã đơn hàng. Vui lòng thử lại.",
        )

    lock.status = "checkout_pending"
    lock.expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.INVENTORY_LOCK_TTL
    )

    # Tạo Order
    new_order = Order(
        user_id=user_id,
        product_id=data.product_id,
        store_id=order_store_id,
        lock_id=lock.id,
        quantity=data.quantity,
        total_amount=total_amount,
        full_name=data.full_name,
        phone=data.phone,
        address=data.address,
        status="PENDING_PAYMENT",
        order_code=order_code,
    )
    db.add(new_order)
    db.flush()
    db.add(
        Payment(
            order_id=new_order.order_id,
            provider=settings.PAYMENT_PROVIDER,
            amount=total_amount,
            status="pending",
            raw_payload={"source": "order_created"},
        )
    )
    _log_event(
        db,
        entity_type="order",
        entity_id=new_order.order_id,
        action="created_pending_payment",
        user_id=user_id,
        payload={
            "lock_id": lock.id,
            "product_id": data.product_id,
            "store_id": order_store_id,
            "quantity": data.quantity,
            "total_amount": total_amount,
        },
    )
    db.commit()
    db.refresh(new_order)
    try:
        await redis.delete(_lock_key(lock.id))
    except Exception:
        logger.warning(
            "Không thể xóa Redis key cho completed lock_id=%s", lock.id, exc_info=True
        )

    return {
        "order_id": new_order.order_id,
        "order_code": new_order.order_code,
        "status": new_order.status,
        "total_amount": total_amount,
        "product_name": product.name,
        "vietqr_url": _build_vietqr_url(total_amount, order_code),
    }


def _verify_payment_signature(data: PaymentWebhook) -> None:
    if not settings.PAYMENT_WEBHOOK_SECRET:
        if settings.ENVIRONMENT != "local" or data.provider != "vietqr_mock":
            raise HTTPException(
                status_code=500, detail="Payment webhook secret chưa được cấu hình."
            )
        return
    if not data.signature:
        raise HTTPException(status_code=401, detail="Thiếu chữ ký webhook.")

    message = f"{data.provider}:{data.transaction_id}:{data.order_code}:{data.amount}:{data.status}"
    expected = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, data.signature):
        raise HTTPException(status_code=401, detail="Chữ ký webhook không hợp lệ.")


def handle_payment_webhook(db: Session, data: PaymentWebhook):
    _verify_payment_signature(data)

    existing_query = db.query(Payment).filter(
        Payment.transaction_id == data.transaction_id
    )
    if data.idempotency_key:
        existing_query = db.query(Payment).filter(
            or_(
                Payment.transaction_id == data.transaction_id,
                Payment.idempotency_key == data.idempotency_key,
            )
        )
    existing = existing_query.first()
    if existing:
        order = db.query(Order).filter(Order.order_id == existing.order_id).first()
        return {
            "order_id": existing.order_id,
            "order_code": order.order_code if order else data.order_code,
            "order_status": order.status if order else "UNKNOWN",
            "payment_status": existing.status,
            "idempotent": True,
        }

    order = (
        db.query(Order)
        .filter(Order.order_code == data.order_code)
        .with_for_update()
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    if order.total_amount != data.amount:
        raise HTTPException(
            status_code=400, detail="Số tiền webhook không khớp đơn hàng."
        )
    if order.status == "PAID":
        existing_paid = (
            db.query(Payment)
            .filter(Payment.order_id == order.order_id, Payment.status == "paid")
            .first()
        )
        return {
            "order_id": order.order_id,
            "order_code": order.order_code,
            "order_status": order.status,
            "payment_status": existing_paid.status if existing_paid else "paid",
            "idempotent": True,
        }
    if order.status != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=409, detail=f"Đơn hàng không còn chờ thanh toán: {order.status}"
        )

    lock = (
        db.query(InventoryLock)
        .filter(InventoryLock.id == order.lock_id)
        .with_for_update()
        .first()
    )
    if not lock:
        raise HTTPException(status_code=409, detail="Không tìm thấy lock của đơn hàng.")

    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == order.product_id,
            Inventory.store_id == order.store_id,
        )
        .with_for_update()
        .first()
    )
    if not inv:
        raise HTTPException(
            status_code=409, detail="Không tìm thấy tồn kho của đơn hàng."
        )

    status_map = {
        "paid": "PAID",
        "failed": "PAYMENT_FAILED",
        "cancelled": "CANCELLED",
    }
    order.status = status_map[data.status]
    if data.status == "paid":
        if lock.status != "checkout_pending":
            raise HTTPException(
                status_code=409, detail="Lock không còn ở trạng thái chờ thanh toán."
            )
        if inv.stock < order.quantity or inv.locked_stock < order.quantity:
            raise HTTPException(
                status_code=409, detail="Tồn kho không đủ để xác nhận thanh toán."
            )
        inv.stock -= order.quantity
        inv.locked_stock -= order.quantity
        lock.status = "completed"
    else:
        if (
            lock.status in {"checkout_pending", "soft_locked"}
            and inv.locked_stock >= order.quantity
        ):
            inv.locked_stock -= order.quantity
        lock.status = data.status

    payment = Payment(
        order_id=order.order_id,
        provider=data.provider,
        amount=data.amount,
        status=data.status,
        transaction_id=data.transaction_id,
        idempotency_key=data.idempotency_key,
        raw_payload=data.model_dump(exclude={"signature"}),
    )
    db.add(payment)
    _log_event(
        db,
        entity_type="order",
        entity_id=order.order_id,
        action=f"payment_{data.status}",
        user_id=order.user_id,
        payload={
            "provider": data.provider,
            "transaction_id": data.transaction_id,
            "amount": data.amount,
        },
    )
    db.commit()

    return {
        "order_id": order.order_id,
        "order_code": order.order_code,
        "order_status": order.status,
        "payment_status": payment.status,
        "idempotent": False,
    }


def get_user_orders(db: Session, user_id: str):
    orders = db.query(Order, Product, Store).join(
        Product, Order.product_id == Product.product_id
    ).outerjoin(
        Store, Order.store_id == Store.store_id
    ).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()

    res = []
    for order, product, store in orders:
        res.append({
            "order_id": order.order_id,
            "order_code": order.order_code,
            "status": order.status,
            "total_amount": order.total_amount,
            "quantity": order.quantity,
            "created_at": order.created_at,
            "product_name": product.name if product else None,
            "store_name": store.name if store else None,
        })
    return res


def get_order(db: Session, order_id: int, user_id: str):
    result = db.query(Order, Product, Store).join(
        Product, Order.product_id == Product.product_id
    ).outerjoin(
        Store, Order.store_id == Store.store_id
    ).filter(Order.order_id == order_id, Order.user_id == user_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    order, product, store = result
    return {
        "order_id": order.order_id,
        "order_code": order.order_code,
        "status": order.status,
        "total_amount": order.total_amount,
        "quantity": order.quantity,
        "created_at": order.created_at,
        "product_name": product.name if product else None,
        "store_name": store.name if store else None,
    }


def cancel_order(db: Session, order_id: int, user_id: str):
    order = db.query(Order).filter(Order.order_id == order_id, Order.user_id == user_id).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    if order.status not in ["PENDING_PAYMENT"]:
        raise HTTPException(status_code=400, detail="Chỉ có thể hủy đơn hàng đang chờ thanh toán")

    order.status = "CANCELLED"

    if order.lock_id:
        lock = db.query(InventoryLock).filter(InventoryLock.id == order.lock_id).with_for_update().first()
        if lock and lock.status == "checkout_pending":
            lock.status = "expired"
            # Return stock
            inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
            if lock.store_id is not None:
                inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
            inv = inv_query.with_for_update().first()

            if inv and inv.locked_stock >= lock.quantity:
                inv.locked_stock -= lock.quantity

    db.commit()
