import logging
import uuid

from sqlalchemy.orm import Session

from app.domains.vision.model import VirtualCloset, VisionTask

logger = logging.getLogger(__name__)

def create_vision_task(db: Session, image_path: str):
    task_id = str(uuid.uuid4())
    new_task = VisionTask(task_id=task_id, image_path=image_path, status="processing")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    try:
        from workers.ai_worker.celery_app import celery_app

        celery_app.send_task(
            "workers.ai_worker.vision_tasks.process_image",
            args=[task_id, image_path],
        )
    except Exception as e:
        new_task.status = "failed"
        new_task.detected_objects = {"error": "Không enqueue được AI worker"}
        db.commit()
        logger.warning("Không enqueue được process_image: %s", e)
    return new_task

def get_vision_task(db: Session, task_id: str):
    return db.query(VisionTask).filter(VisionTask.task_id == task_id).first()

def add_to_closet(db: Session, user_id: str, image_path: str):
    # Khởi tạo None ngay lập tức, vì Vector thực sẽ được chạy ngầm bởi AI Celery
    new_item = VirtualCloset(
        user_id=user_id,
        image_path=image_path,
        vector_embedding=None
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # Ném công việc nặng (AI Vision Embeddings) cho Background Worker
    try:
        from workers.ai_worker.celery_app import celery_app

        celery_app.send_task(
            "workers.ai_worker.vision_tasks.process_closet_image",
            args=[new_item.id, image_path],
        )
    except Exception as e:
        logger.warning("Không enqueue được process_closet_image: %s", e)

    return new_item

def get_user_closet(db: Session, user_id: str):
    return db.query(VirtualCloset).filter(VirtualCloset.user_id == user_id).all()


def find_similar_products_for_closet(db: Session, closet_item_id: int, user_id: str, top_n: int = 5):
    """
    Mix & Match API thật: Lấy vector 512D của closet item → tìm products
    có cosine similarity cao nhất bằng pgvector.

    Trả về list[dict] gồm product info + match_score (0-100%).
    """
    from app.domains.inventory.model import Inventory, Product

    closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_item_id).first()
    if not closet_item:
        return None, "Closet item not found"

    if str(closet_item.user_id) != str(user_id):
        return None, "Forbidden: Không có quyền truy cập tủ đồ này"

    if closet_item.vector_embedding is None:
        return None, "Vector chưa được xử lý. Vui lòng chờ AI Worker hoàn tất."

    # Query pgvector: cosine_distance trả về khoảng cách [0, 2]
    # 0 = giống hoàn toàn, 2 = đối lập hoàn toàn
    # Chỉ tìm products đã có embedding
    query = db.query(
        Product,
        Product.embedding.cosine_distance(closet_item.vector_embedding).label("distance")
    ).filter(
        Product.embedding.is_not(None)
    ).order_by(
        Product.embedding.cosine_distance(closet_item.vector_embedding)
    ).limit(top_n)

    results = query.all()

    matches = []
    for product, distance in results:
        # Convert cosine distance → similarity percentage
        # distance ∈ [0, 2] → similarity = (1 - distance/2) * 100
        similarity = round((1.0 - float(distance) / 2.0) * 100, 1)

        # Lấy thông tin tồn kho
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        stock = inv.stock if inv else 0
        store_id = inv.store_id if inv else None

        matches.append({
            "product_id": product.product_id,
            "name": product.name,
            "description": product.description,
            "price": inv.price_override if inv and inv.price_override is not None else product.price,
            "original_price": product.original_price,
            "image_url": product.image_url,
            "match_score": similarity,
            "stock": stock,
            "store_id": store_id,
        })

    return matches, None


def find_similar_products_for_product(db: Session, product_id: int, top_n: int = 5):
    from app.domains.inventory.model import Inventory, Product

    source = db.query(Product).filter(Product.product_id == product_id).first()
    if not source:
        return None, "Product not found"
    if source.embedding is None:
        return None, "Product chưa có vector embedding."

    results = db.query(
        Product,
        Product.embedding.cosine_distance(source.embedding).label("distance"),
    ).filter(
        Product.embedding.is_not(None),
        Product.product_id != product_id,
    ).order_by(
        Product.embedding.cosine_distance(source.embedding)
    ).limit(top_n).all()

    matches = []
    for product, distance in results:
        similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        matches.append({
            "product_id": product.product_id,
            "name": product.name,
            "description": product.description,
            "price": inv.price_override if inv and inv.price_override is not None else product.price,
            "original_price": product.original_price,
            "image_url": product.image_url,
            "match_score": similarity,
            "stock": inv.stock if inv else 0,
            "store_id": inv.store_id if inv else None,
        })

    return matches, None
