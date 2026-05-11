from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class VisionUploadResponse(BaseModel):
    task_id: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    image_path: str
    detected_objects: Optional[Dict] = None
    matched_product_ids: Optional[List[int]] = None
    class Config:
        from_attributes = True

class ClosetItemResponse(BaseModel):
    id: int
    user_id: int
    image_path: str
    created_at: datetime
    class Config:
        from_attributes = True


class MixMatchProduct(BaseModel):
    product_id: int
    name: str
    description: Optional[str] = None
    price: int
    original_price: Optional[int] = None
    image_url: Optional[str] = None
    match_score: float        # 0-100%
    stock: int = 0
    store_id: Optional[int] = None


class MixMatchResponse(BaseModel):
    closet_item_id: int
    matches: List[MixMatchProduct]
    total_matches: int

