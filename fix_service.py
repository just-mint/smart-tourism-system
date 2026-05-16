import re

with open('backend/app/domains/inventory/service.py', 'r') as f:
    content = f.read()

pattern = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> main\n', re.DOTALL)
matches = list(pattern.finditer(content))

# matches[0]: lock_key
m0 = """    if not getattr(request, "store_id", None):
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp store_id để khóa hàng cho cửa hàng cụ thể.")
    lock_key = _lock_key(request.product_id, request.store_id)
"""

# matches[1]: phase 2 postgres row lock
m1 = """    inv_query = db.query(Inventory).filter(Inventory.product_id == request.product_id)
    if request.store_id:
        inv_query = inv_query.filter(Inventory.store_id == request.store_id)
    inv = inv_query.with_for_update().first()
"""

# matches[2]: kiểm tra tồn kho
m2 = """    # Lấy TỔNG tồn kho có sẵn từ TẤT CẢ Store có bán product này nếu không có store_id cụ thể
    total_available_query = db.query(Inventory).filter(Inventory.product_id == request.product_id)
    if request.store_id:
        total_available_query = total_available_query.filter(Inventory.store_id == request.store_id)

    total_available = sum(max(0, i.stock - i.locked_stock) for i in total_available_query.all())

    if total_available < request.quantity:
        await redis.delete(lock_key)
        raise HTTPException(status_code=400, detail=f"Không đủ hàng. Tồn kho còn: {total_available}")
"""

# matches[3]: store_id = request.store_id or inv.store_id
m3 = """        store_id=request.store_id or inv.store_id,
"""

# matches[4]: ttl redis key
m4 = """            ttl = await redis.ttl(_lock_key(lock.product_id, lock.store_id))
"""

# matches[5]: store_id
m5 = """            "store_id": lock.store_id,
"""

# matches[6]: check_and_release_expired_locks
m6 = """        inv_query = db.query(Inventory).filter(Inventory.product_id == lock.product_id)
        if lock.store_id is not None:
            inv_query = inv_query.filter(Inventory.store_id == lock.store_id)
        inv = inv_query.with_for_update().first()
"""

# matches[7]: finalize_order logic
m7 = """    # Yêu cầu phải có lock_id kèm theo
    if not getattr(data, "lock_id", None):
        raise HTTPException(status_code=400, detail="Phải cung cấp lock_id khi tạo đơn hàng.")

    lock = db.query(InventoryLock).filter(InventoryLock.id == data.lock_id).first()
    if not lock or lock.user_id != user_id or lock.status != "soft_locked":
        raise HTTPException(status_code=400, detail="Lock không hợp lệ hoặc đã hết hạn.")
    if lock.product_id != data.product_id or lock.quantity != data.quantity:
        raise HTTPException(status_code=400, detail="Thông tin lock không khớp với đơn hàng.")

    order_store_id = lock.store_id

    # Xóa Redis lock (per-store key)
    lock_key = _lock_key(data.product_id, order_store_id)
    try:
        await redis.delete(lock_key)
    except Exception:
        pass

    # Trừ tồn kho vĩnh viễn tại cửa hàng được lock
    inv = db.query(Inventory).filter(
        Inventory.product_id == data.product_id,
        Inventory.store_id == order_store_id,
    ).with_for_update().first()

    if inv:
        if inv.stock < data.quantity:
            raise HTTPException(status_code=400, detail="Tồn kho không còn đủ để tạo đơn.")
        inv.stock = max(0, inv.stock - data.quantity)
        inv.locked_stock = max(0, inv.locked_stock - data.quantity)
        unit_price = inv.price_override if inv.price_override is not None else product.price
    else:
        raise HTTPException(status_code=404, detail="Không tìm thấy tồn kho cho sản phẩm đã giữ.")

    total_amount = int(unit_price * data.quantity)

    for _ in range(5):
        order_code = _generate_order_code()
        if not db.query(Order).filter(Order.order_code == order_code).first():
            break
    else:
        raise HTTPException(status_code=500, detail="Hệ thống bận, không thể tạo mã đơn hàng. Vui lòng thử lại.")

    lock.status = "completed"
"""

# matches[8]: new_order store_id
m8 = """        store_id=order_store_id,
"""

# matches[9]: vietqr_url
m9 = """    vietqr_url = _build_vietqr_url(total_amount, order_code)
"""

replacements = [m0, m1, m2, m3, m4, m5, m6, m7, m8, m9]

new_content = content
for i, match in enumerate(matches):
    if i < len(replacements):
        new_content = new_content.replace(match.group(0), replacements[i])

with open('backend/app/domains/inventory/service.py', 'w') as f:
    f.write(new_content)

