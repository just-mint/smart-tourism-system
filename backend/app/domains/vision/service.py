from sqlalchemy.orm import Session
from app.domains.vision.model import VisionTask, VirtualCloset
import uuid
import logging

logger = logging.getLogger(__name__)


def create_vision_task(db: Session, image_path: str):
    task_id = str(uuid.uuid4())
    new_task = VisionTask(task_id=task_id, image_path=image_path, status="processing")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Dispatch qua Celery queue (RabbitMQ) thay vì threading.Thread
    # Celery .delay() gửi message vào broker → worker nhận và xử lý bất đồng bộ
    try:
        from workers.ai_worker.vision_tasks import process_image
        process_image.delay(task_id, image_path)
        logger.info(f"[Vision] Đã gửi task {task_id} vào Celery queue (process_image)")
    except Exception as e:
        # Nếu broker không khả dụng, đánh dấu task failed ngay để tránh treo mãi
        logger.error(f"[Vision] Không thể dispatch task lên Celery: {e}")
        new_task.status = "failed"
        new_task.detected_objects = {"error": f"Celery broker unavailable: {str(e)}"}
        db.commit()

    return new_task


def get_vision_task(db: Session, task_id: str):
    return db.query(VisionTask).filter(VisionTask.task_id == task_id).first()


def add_to_closet(db: Session, user_id: str, image_path: str):
    new_item = VirtualCloset(
        user_id=user_id,
        image_path=image_path,
        vector_embedding=None
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # Dispatch qua Celery queue thay vì threading.Thread
    try:
        from workers.ai_worker.vision_tasks import process_closet_image
        process_closet_image.delay(new_item.id, image_path)
        logger.info(f"[Vision] Đã gửi closet item {new_item.id} vào Celery queue (process_closet_image)")
    except Exception as e:
        logger.error(f"[Vision] Không thể dispatch closet task lên Celery: {e}")
        # Không fail hard ở đây — item đã lưu, embedding sẽ là None
        # Worker có thể retry sau bằng Celery Beat nếu cần

    return new_item


def get_user_closet(db: Session, user_id: str):
    return db.query(VirtualCloset).filter(VirtualCloset.user_id == user_id).all()


def find_similar_products_for_closet(db: Session, closet_item_id: int, top_n: int = 5):
    """
    Mix & Match API: Lấy vector 512D của closet item → tìm products
    có cosine similarity cao nhất bằng pgvector.
    """
    from app.domains.inventory.model import Product, Inventory

    closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_item_id).first()
    if not closet_item:
        return None, "Closet item not found"

    if closet_item.vector_embedding is None:
        return None, "Vector chưa được xử lý. Vui lòng chờ AI Worker hoàn tất."

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
        similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        stock = inv.stock if inv else 0
        store_id = inv.store_id if inv else None
        matches.append({
            "product_id": product.product_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "original_price": product.original_price,
            "image_url": product.image_url,
            "match_score": similarity,
            "stock": stock,
            "store_id": store_id,
        })

    return matches, None