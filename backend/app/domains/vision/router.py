from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid
from app.db.session import get_db
from app.domains.vision import service, schema
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User

router = APIRouter()

ALLOWED_TYPES = settings.ALLOWED_IMAGE_TYPES
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_and_save(file: UploadFile, folder: str) -> str:
    """Kiểm tra MIME type + dung lượng file trước khi lưu với tên UUID4 chống ghi đè."""
    # 1. Kiểm tra MIME type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Chỉ chấp nhận ảnh JPEG/PNG/WebP. Bạn đã gửi: {file.content_type}"
        )

    # 2. Đọc toàn bộ vào memory để kiểm tra kích thước (an toàn với file nhỏ)
    contents = file.file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File vượt giới hạn {settings.MAX_UPLOAD_SIZE_MB}MB. Kích thước thực: {len(contents) // 1024 // 1024}MB"
        )

    # 3. Tạo thư mục và lưu file an toàn
    #    ⚠️ Dùng UUID4 thay vì tên gốc để chống ghi đè + path traversal
    os.makedirs(folder, exist_ok=True)
    original_name = file.filename or "upload"
    _, ext = os.path.splitext(original_name)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(folder, safe_filename)
    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    return file_path


@router.post("/scan", response_model=schema.VisionUploadResponse)
def upload_and_scan(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload ảnh để AI scan sản phẩm (non-blocking, trả task_id ngay)"""
    file_path = validate_and_save(file, "uploads/scans/")
    task = service.create_vision_task(db=db, image_path=file_path)
    return {"task_id": task.task_id, "message": "Ảnh đang được AI xử lý. Dùng task_id để polling kết quả."}


@router.get("/tasks/{task_id}", response_model=schema.TaskStatus)
def check_task_status(task_id: str, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    task = service.get_vision_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    
    if task.status == "processing":
        delta = (datetime.now(timezone.utc) - task.created_at).total_seconds()
        if delta > 30:
            task.status = "failed"
            task.detected_objects = {"error": "AI Worker Timeout"}
            db.commit()
            
    return task


@router.post("/closet", response_model=schema.ClosetItemResponse)
def add_virtual_closet(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload trang phục cá nhân vào Tủ Đồ Ảo (lưu Vector Embedding 512D qua pgvector)"""
    file_path = validate_and_save(file, "uploads/closet/")
    item = service.add_to_closet(db=db, user_id=current_user.id, image_path=file_path)
    return item


@router.get("/closet", response_model=list[schema.ClosetItemResponse])
def my_closet(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_user_closet(db=db, user_id=current_user.id)


@router.get("/closet/{item_id}/matches", response_model=schema.MixMatchResponse)
def get_mix_match(item_id: int, db: Session = Depends(get_db)):
    """
    AI Mix & Match: Tìm sản phẩm trong catalog có visual similarity cao nhất
    so với một item trong tủ đồ ảo. Dùng pgvector cosine_distance trên CLIP 512D embeddings.
    """
    matches, error = service.find_similar_products_for_closet(db=db, closet_item_id=item_id, top_n=5)
    if matches is None:
        raise HTTPException(status_code=404, detail=error)
    return schema.MixMatchResponse(
        closet_item_id=item_id,
        matches=matches,
        total_matches=len(matches),
    )


@router.get("/products/{product_id}/matches", response_model=schema.ProductMatchResponse)
def get_product_matches(product_id: int, db: Session = Depends(get_db)):
    """
    Product-to-product visual matching. Use this when the UI starts from a
    catalog product rather than a user's virtual closet item.
    """
    matches, error = service.find_similar_products_for_product(db=db, product_id=product_id, top_n=5)
    if matches is None:
        raise HTTPException(status_code=404, detail=error)
    return schema.ProductMatchResponse(
        product_id=product_id,
        matches=matches,
        total_matches=len(matches),
    )

