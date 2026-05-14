from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class ProductResponse(BaseModel):
    product_id: int
    name: str
    price: float
    original_price: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = 0
    store_id: Optional[int] = None
    class Config:
        from_attributes = True

class LockRequest(BaseModel):
    product_id: int
    quantity: int = 1

class LockResponseItem(BaseModel):
    id: int
    product_id: int
    quantity: int
    status: str
    ttl_seconds: int
    expires_at: datetime
    class Config:
        from_attributes = True

class StoreResponse(BaseModel):
    store_id: int
    place_id: Optional[str] = None
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    class Config:
        from_attributes = True

# --- Search ---
class SearchResult(BaseModel):
    stores: list[StoreResponse] = []
    products: list[ProductResponse] = []

# --- Order / Checkout ---
class OrderCreate(BaseModel):
    product_id: int
    store_id: Optional[int] = None
    quantity: int = 1
    full_name: str
    phone: str
    address: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "")
        if not cleaned.isdigit() or len(cleaned) < 9 or len(cleaned) > 11:
            raise ValueError("Số điện thoại không hợp lệ (9-11 chữ số)")
        return cleaned

    @field_validator("full_name", "address")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Trường này không được để trống")
        return v.strip()

class OrderResponse(BaseModel):
    order_id: int
    order_code: str
    status: str
    total_amount: int
    product_name: str
    vietqr_url: str
    class Config:
        from_attributes = True
