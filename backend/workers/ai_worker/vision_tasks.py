from workers.ai_worker.celery_app import celery_app
from sentence_transformers import SentenceTransformer
from PIL import Image
import logging

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

logger.info(
    "[AI-Worker] Loading CLIP model (clip-ViT-B-32). First start can take a while..."
)
try:
    model = SentenceTransformer("clip-ViT-B-32")
    logger.info("[AI-Worker] CLIP model loaded.")
except Exception as e:
    logger.error(f"[AI-Worker] Failed to initialize CLIP model: {e}")
    model = None


def _mark_task_failed(task_id: str, error: str):
    db = SessionLocal()
    try:
        from app.domains.vision.model import VisionTask

        task = db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
        if task:
            task.status = "failed"
            task.detected_objects = {"error": error}
            db.commit()
    finally:
        db.close()


def _ensure_product_embeddings(db, Product):
    products = db.query(Product).filter(Product.embedding.is_(None)).all()
    if not products:
        return 0

    texts = [
        " - ".join(
            part
            for part in [
                product.name,
                product.description,
                getattr(product, "category", None),
            ]
            if part
        )
        for product in products
    ]
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False).tolist()
    for product, embedding in zip(products, embeddings):
        product.embedding = embedding
    db.commit()
    logger.info(f"[AI-Worker] Generated embeddings for {len(products)} products")
    return len(products)


@celery_app.task(name="workers.ai_worker.vision_tasks.process_image")
def process_image(task_id: str, image_path: str):
    """Process /vision/scan: embed the uploaded image and find similar products."""
    if model is None:
        error = "Model CLIP chua san sang trong AI worker."
        _mark_task_failed(task_id, error)
        return {"task_id": task_id, "status": "failed", "error": error}

    db = None
    try:
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()

        db = SessionLocal()
        from app.domains.inventory.model import Inventory, Product
        from app.domains.vision.model import VisionTask

        task = db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
        if not task:
            return {"status": "error", "message": "Task not found"}

        _ensure_product_embeddings(db, Product)

        similar_products = (
            db.query(
                Product,
                Product.embedding.cosine_distance(img_emb).label("distance"),
            )
            .filter(Product.embedding.is_not(None))
            .order_by(Product.embedding.cosine_distance(img_emb))
            .limit(4)
            .all()
        )

        similar_items = []
        matched_ids = []
        for product, distance in similar_products:
            similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
            inv = (
                db.query(Inventory)
                .filter(Inventory.product_id == product.product_id)
                .first()
            )
            similar_items.append(
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "original_price": product.original_price,
                    "image_url": product.image_url,
                    "match_score": similarity,
                    "stock": inv.stock if inv else 0,
                    "store_id": inv.store_id if inv else None,
                }
            )
            matched_ids.append(product.product_id)

        task.matched_product_ids = matched_ids
        task.detected_objects = {"similar_items": similar_items}
        task.status = "completed"
        db.commit()

        logger.info(f"[AI-Worker] Scan completed for task {task_id}: {matched_ids}")
        return {"task_id": task_id, "status": "completed", "matches": matched_ids}

    except Exception as e:
        error = str(e)
        logger.error(f"[AI-Worker] Scan failed for task {task_id}: {error}")
        _mark_task_failed(task_id, error)
        return {"task_id": task_id, "status": "failed", "error": error}
    finally:
        if db is not None:
            db.close()


@celery_app.task(name="workers.ai_worker.vision_tasks.process_closet_image")
def process_closet_image(closet_id: int, image_path: str):
    """Process /vision/closet: store the uploaded outfit embedding."""
    if model is None:
        return {"status": "error", "message": "Model CLIP chua san sang"}

    db = None
    try:
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()

        db = SessionLocal()
        from app.domains.vision.model import VirtualCloset

        closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_id).first()
        if closet_item:
            closet_item.vector_embedding = img_emb
            db.commit()

        logger.info(f"[AI-Worker] Stored closet embedding for item {closet_id}")
        return {"status": "completed", "closet_id": closet_id}
    except Exception as e:
        logger.error(f"[AI-Worker] Closet processing failed for {closet_id}: {e}")
        return {"status": "failed", "closet_id": closet_id, "error": str(e)}
    finally:
        if db is not None:
            db.close()
