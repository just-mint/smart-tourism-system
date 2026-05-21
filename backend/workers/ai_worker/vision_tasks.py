import logging
from datetime import datetime, timezone

from PIL import Image
from sentence_transformers import SentenceTransformer

from app.db.session import SessionLocal
from workers.ai_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Tải CLIP Model vào RAM 1 lần duy nhất (Singleton Pattern)
logger.info(
    "[AI-Worker] Đang tải Model ôm trọn CLIP (clip-ViT-B-32) - Sẽ mất vài chục giây lần đầu..."
)
try:
    # Model này nhận ảnh thật và sinh ra Vector_512D chuẩn xác
    model = SentenceTransformer("clip-ViT-B-32")
    logger.info("[AI-Worker] ✅ Model CLIP đã được nạp hoàn tất!")
except Exception as e:
    logger.error(f"[AI-Worker] ❌ Lỗi khởi tạo model CLIP: {e}")
    model = None


def _mark_scan_failed(task_id: str, message: str) -> None:
    db = SessionLocal()
    try:
        from app.domains.vision.model import VisionTask

        task = db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
        if task:
            task.status = "failed"
            task.detected_objects = {"error": message}
            db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            f"[AI-Worker] Không thể cập nhật trạng thái failed cho task {task_id}: {exc}"
        )
    finally:
        db.close()


@celery_app.task(name="workers.ai_worker.vision_tasks.process_image")
def process_image(task_id: str, image_path: str):
    """Xử lý API /scan - Tìm kiếm sản phẩm tương tự từ ảnh"""
    if model is None:
        _mark_scan_failed(task_id, "Model chưa sẵn sàng")
        return {"status": "error", "message": "Model chưa sẵn sàng"}

    db = None
    try:
        # Load ảnh và sinh Vector
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()  # Dòng này biến ảnh thành mảng 512D float

        db = SessionLocal()
        from app.domains.inventory.model import Inventory, Product, Store
        from app.domains.vision.model import VisionTask

        # 1. Update Task status
        task = db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
        if not task:
            return {"status": "error", "message": "Task not found"}

        # 2. Tìm SP tương tự bằng PGVECTOR Cosine Similarity (<=>)
        similar_products = (
            db.query(
                Product, Product.embedding.cosine_distance(img_emb).label("distance")
            )
            .filter(Product.embedding.is_not(None))
            .order_by(Product.embedding.cosine_distance(img_emb))
            .limit(4)
            .all()
        )

        matched_ids = [p.product_id for p, _ in similar_products]

        # 3. Tìm cửa hàng còn hàng (JOIN Inventory và Store)
        product_stores = {}
        if matched_ids:
            inv_store_records = (
                db.query(Inventory, Store)
                .join(Store, Inventory.store_id == Store.store_id)
                .filter(Inventory.product_id.in_(matched_ids), Inventory.stock > 0)
                .all()
            )

            for inv, store in inv_store_records:
                if inv.product_id not in product_stores:
                    product_stores[inv.product_id] = []

                product_stores[inv.product_id].append(
                    {
                        "store_id": store.store_id,
                        "name": store.name,
                        "lat": float(store.lat) if store.lat else None,
                        "lon": float(store.lon) if store.lon else None,
                        "stock": inv.stock,
                        "address": store.address,
                        "rating": float(store.rating) if store.rating else None,
                        "category": store.category,
                    }
                )

        similar_items = []
        for product, distance in similar_products:
            similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
            similar_items.append(
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "image_url": product.image_url,
                    "match_score": similarity,
                    "available_stores": product_stores.get(product.product_id, []),
                }
            )

        # Update
        task.matched_product_ids = matched_ids
        task.detected_objects = {"similar_items": similar_items}
        task.status = "completed"
        db.commit()

        logger.info(
            f"[AI-Worker] ✅ Scan xong Task: {task_id}. Tìm thấy matches: {matched_ids}"
        )
        return {"task_id": task_id, "status": "completed", "matches": matched_ids}

    except Exception as e:
        logger.error(f"[AI-Worker] Lỗi quá trình scan: {e}")
        if db is not None:
            db.rollback()
            try:
                from app.domains.vision.model import VisionTask

                task = (
                    db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
                )
                if task:
                    task.status = "failed"
                    task.detected_objects = {"error": str(e)}
                    db.commit()
            except Exception as status_error:
                db.rollback()
                logger.error(
                    f"[AI-Worker] Không thể lưu lỗi scan task {task_id}: {status_error}"
                )
        else:
            _mark_scan_failed(task_id, str(e))
        return {"task_id": task_id, "status": "failed", "error": str(e)}
    finally:
        if db is not None:
            db.close()


@celery_app.task(name="workers.ai_worker.vision_tasks.process_closet_image")
def process_closet_image(closet_id: int, image_path: str):
    """Xử lý API /closet - Nạp Vector trang phục vào Tủ Đồ Ảo cá nhân"""
    if model is None:
        return {"status": "error"}

    db = None
    try:
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()

        db = SessionLocal()
        from app.domains.vision.model import VirtualCloset

        closet_item = (
            db.query(VirtualCloset).filter(VirtualCloset.id == closet_id).first()
        )
        if closet_item:
            closet_item.vector_embedding = img_emb
            closet_item.embedding_model = "clip-ViT-B-32"
            closet_item.embedding_version = "sentence-transformers"
            closet_item.embedded_at = datetime.now(timezone.utc)
            db.commit()
        logger.info(
            f"[AI-Worker] ✅ Đã lưu Vector 512D cho tủ đồ cá nhân Item ID: {closet_id}"
        )
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.error(f"[AI-Worker] Lỗi xử lý Closet {closet_id}: {e}")
    finally:
        if db is not None:
            db.close()
