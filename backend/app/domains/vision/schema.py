from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VisionUploadResponse(BaseModel):
    task_id: str
    message: str


class TaskStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    status: str
    image_path: str
    detected_objects: dict | None = None
    matched_product_ids: list[int] | None = None


class ClosetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    image_path: str
    created_at: datetime


class MixMatchProduct(BaseModel):
    product_id: int
    name: str
    description: str | None = None
    price: int
    original_price: int | None = None
    image_url: str | None = None
    match_score: float  # 0-100%
    stock: int = 0
    store_id: int | None = None


class MixMatchResponse(BaseModel):
    closet_item_id: int
    matches: list[MixMatchProduct]
    total_matches: int


class ProductMatchResponse(BaseModel):
    product_id: int
    matches: list[MixMatchProduct]
    total_matches: int
