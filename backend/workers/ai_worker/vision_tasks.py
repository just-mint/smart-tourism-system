from workers.ai_worker.celery_app import celery_app
from sentence_transformers import SentenceTransformer
from PIL import Image
import os
import logging
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Tải CLIP Model vào RAM 1 lần duy nhất (Singleton Pattern)
logger.info("[AI-Worker] Đang tải Model ôm trọn CLIP (clip-ViT-B-32) - Sẽ mất vài chục giây lần đầu...")
try:
    # Model này nhận ảnh thật và sinh ra Vector_512D chuẩn xác
    model = SentenceTransformer('clip-ViT-B-32')
    logger.info("[AI-Worker] ✅ Model CLIP đã được nạp hoàn tất!")
except Exception as e:
    logger.error(f"[AI-Worker] ❌ Lỗi khởi tạo model CLIP: {e}")
    model = None

@celery_app.task(name="workers.ai_worker.vision_tasks.process_image")
def process_image(self, task_id: str, image_path: str):
    """Xử lý API /scan - Tìm kiếm sản phẩm tương tự từ ảnh"""
    db = SessionLocal()
    from app.domains.vision.model import VisionTask
    from app.domains.inventory.model import Product
    
    task = db.query(VisionTask).filter(VisionTask.task_id == task_id).first()
    if not task:
        db.close()
        return {"status": "error", "message": "Task not found in DB"}

    if model is None:
        # Xử lý ngay lỗi Model chưa sẵn sàng vào DB
        task.status = "failed"
        task.detected_objects = {"error": "AI Model chưa sẵn sàng hoặc bị lỗi khởi tạo."}
        db.commit()
        db.close()
        return {"status": "error", "message": "Model chưa sẵn sàng"}

    try:
        # Load ảnh và sinh Vector
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()

        # Tìm SP tương tự bằng PGVECTOR Cosine Similarity (<=>)
        similar_products = db.query(
            Product,
            Product.embedding.cosine_distance(img_emb).label("distance")
        ).filter(
            Product.embedding.is_not(None)
        ).order_by(
            Product.embedding.cosine_distance(img_emb)
        ).limit(4).all()

        similar_items = []
        matched_ids = []
        for product, distance in similar_products:
            similarity = round((1.0 - float(distance) / 2.0) * 100, 1)
            similar_items.append({
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "image_url": product.image_url,
                "match_score": similarity
            })
            matched_ids.append(product.product_id)

        # Update thành công
        task.matched_product_ids = matched_ids
        task.detected_objects = {"similar_items": similar_items}
        task.status = "completed"
        db.commit()

        logger.info(f"[AI-Worker] ✅ Scan xong Task: {task_id}. Tìm thấy matches: {matched_ids}")
        return {"task_id": task_id, "status": "completed", "matches": matched_ids}
        
    except Exception as e:
        # --- P1-22: UPDATE TASK FAILED VÀO DB ---
        db.rollback() # Hủy các query đang lơ lửng để tránh treo Session
        
        # Ghi đè lỗi vào JSON để Frontend đọc được và hiển thị thông báo
        task.status = "failed"
        task.detected_objects = {"error": f"Lỗi xử lý ảnh AI: {str(e)}"} 
        db.commit()
        
        logger.error(f"[AI-Worker] ❌ Lỗi quá trình scan (đã update DB failed): {e}")
        return {"task_id": task_id, "status": "failed", "error": str(e)}
        
    finally:
        # Luôn luôn đóng connection DB dù thành công hay thất bại
        db.close()

@celery_app.task(name="workers.ai_worker.vision_tasks.process_closet_image")
def process_closet_image(closet_id: int, image_path: str):
    """Xử lý API /closet - Nạp Vector trang phục vào Tủ Đồ Ảo cá nhân"""
    if model is None:
        logger.error("[AI-Worker] Model chưa sẵn sàng cho closet")
        return {"status": "error"}
    
    db = SessionLocal()
    from app.domains.vision.model import VirtualCloset
    
    try:
        img = Image.open(image_path)
        img_emb = model.encode(img).tolist()

        closet_item = db.query(VirtualCloset).filter(VirtualCloset.id == closet_id).first()
        if closet_item:
            closet_item.vector_embedding = img_emb
            db.commit()
            
        logger.info(f"[AI-Worker] ✅ Đã lưu Vector 512D cho tủ đồ cá nhân Item ID: {closet_id}")
        
    except Exception as e:
        # P1-22 cho Closet: Bắt lỗi và Rollback
        db.rollback()
        logger.error(f"[AI-Worker] ❌ Lỗi xử lý Closet {closet_id}: {e}")
        
    finally:
        db.close()