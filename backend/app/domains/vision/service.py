from sqlalchemy.orm import Session
from app.domains.vision.model import VisionTask, VirtualCloset
import uuid
import logging
import threading

logger = logging.getLogger(__name__)

def create_vision_task(db: Session, image_path: str):
    task_id = str(uuid.uuid4())
    new_task = VisionTask(task_id=task_id, image_path=image_path, status="processing")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    try:
        from workers.ai_worker.vision_tasks import process_image
        process_image.delay(task_id, image_path)
    except Exception as e:
        logger.warning(f"Lỗi khi xử lý process_image bằng Thread: {e}")
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
        from workers.ai_worker.vision_tasks import process_closet_image
        process_closet_image.delay(new_item.id, image_path)
    except Exception as e:
        logger.warning(f"Lỗi khi xử lý process_closet_image bằng Thread: {e}")

    return new_item

def get_user_closet(db: Session, user_id: str):
    return db.query(VirtualCloset).filter(VirtualCloset.user_id == user_id).all()


def find_similar_products_for_closet(db: Session, closet_item_id: int, top_n: int = 5):
    """
    Mix & Match API thật: Lấy vector 512D của closet item → tìm products 
    có cosine similarity cao nhất bằng pgvector.
    
    Trả về list[dict] gồm product info + match_score (0-100%).
    """
    from app.domains.inventory.model import Product, Inventory

    closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_item_id).first()
    if not closet_item:
        return None, "Closet item not found"

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
            "price": product.price,
            "original_price": product.original_price,
            "image_url": product.image_url,
            "match_score": similarity,
            "stock": stock,
            "store_id": store_id,
        })

    return matches, None


def find_similar_products_for_product(db: Session, product_id: int, top_n: int = 5):
    """
    Product-to-product visual matching for catalog items.
    This is intentionally separate from closet matching so callers do not pass
    Product.product_id into /closet/{item_id}/matches by mistake.
    """
    from app.domains.inventory.model import Product

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return None, "Product not found"

    if product.embedding is None:
        return None, "Product chÆ°a cĂ³ vector embedding."

    return _find_similar_products_by_embedding(
        db=db,
        embedding=product.embedding,
        top_n=top_n,
        exclude_product_id=product_id,
    ), None


def _find_similar_products_by_embedding(
    db: Session,
    embedding,
    top_n: int = 5,
    exclude_product_id: int | None = None,
):
    from app.domains.inventory.model import Product, Inventory

    query = db.query(
        Product,
        Product.embedding.cosine_distance(embedding).label("distance")
    ).filter(
        Product.embedding.is_not(None)
    )

    if exclude_product_id is not None:
        query = query.filter(Product.product_id != exclude_product_id)

    results = query.order_by(
        Product.embedding.cosine_distance(embedding)
    ).limit(top_n).all()

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

    return matches

