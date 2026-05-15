import logging
import uuid

from sqlalchemy.orm import Session

from app.domains.vision.model import VirtualCloset, VisionTask

logger = logging.getLogger(__name__)


def _send_celery_task(task_name: str, args: list):
    from workers.ai_worker.celery_app import celery_app

    celery_app.send_task(task_name, args=args)


def create_vision_task(db: Session, image_path: str):
    task_id = str(uuid.uuid4())
    new_task = VisionTask(task_id=task_id, image_path=image_path, status="processing")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    try:
        _send_celery_task(
            "workers.ai_worker.vision_tasks.process_image",
            [task_id, image_path],
        )
    except Exception as e:
        logger.warning(f"Khong gui duoc task process_image sang Celery: {e}")

    return new_task


def get_vision_task(db: Session, task_id: str):
    return db.query(VisionTask).filter(VisionTask.task_id == task_id).first()


def add_to_closet(db: Session, user_id: str, image_path: str):
    new_item = VirtualCloset(
        user_id=user_id,
        image_path=image_path,
        vector_embedding=None,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    try:
        _send_celery_task(
            "workers.ai_worker.vision_tasks.process_closet_image",
            [new_item.id, image_path],
        )
    except Exception as e:
        logger.warning(f"Khong gui duoc task process_closet_image sang Celery: {e}")

    return new_item


def get_user_closet(db: Session, user_id: str):
    return db.query(VirtualCloset).filter(VirtualCloset.user_id == user_id).all()


def find_similar_products_for_closet(db: Session, closet_item_id: int, top_n: int = 5):
    from app.domains.inventory.model import Inventory, Product
    from app.domains.inventory.service import _product_image_url

    closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_item_id).first()
    if not closet_item:
        return None, "Closet item not found"

    if closet_item.vector_embedding is None:
        return None, "Vector chua duoc xu ly. Vui long cho AI Worker hoan tat."

    query = (
        db.query(
            Product,
            Product.embedding.cosine_distance(closet_item.vector_embedding).label(
                "distance"
            ),
        )
        .filter(Product.embedding.is_not(None))
        .order_by(Product.embedding.cosine_distance(closet_item.vector_embedding))
        .limit(top_n)
    )

    matches = []
    for product, distance in query.all():
        similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()
        matches.append(
            {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "original_price": product.original_price,
                "image_url": _product_image_url(product),
                "match_score": similarity,
                "stock": inv.stock if inv else 0,
                "store_id": inv.store_id if inv else None,
            }
        )

    return matches, None


def find_similar_products_for_product(db: Session, product_id: int, top_n: int = 5):
    from app.domains.inventory.model import Product

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return None, "Product not found"

    if product.embedding is None:
        return None, "Product chua co vector embedding."

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
    from app.domains.inventory.model import Inventory, Product
    from app.domains.inventory.service import _product_image_url

    query = db.query(
        Product,
        Product.embedding.cosine_distance(embedding).label("distance"),
    ).filter(Product.embedding.is_not(None))

    if exclude_product_id is not None:
        query = query.filter(Product.product_id != exclude_product_id)

    results = query.order_by(Product.embedding.cosine_distance(embedding)).limit(top_n).all()

    matches = []
    for product, distance in results:
        similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
        inv = db.query(Inventory).filter(Inventory.product_id == product.product_id).first()

        matches.append(
            {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "original_price": product.original_price,
                "image_url": _product_image_url(product),
                "match_score": similarity,
                "stock": inv.stock if inv else 0,
                "store_id": inv.store_id if inv else None,
            }
        )

    return matches
