from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProductResponse(BaseModel):
    product_id: int
    name: str
    price: float
    original_price: int | None = None
    description: str | None = None
    image_url: str | None = None
    stock: int | None = 0
    store_id: int | None = None
    class Config:
        from_attributes = True

class LockRequest(BaseModel):
    product_id: int
    store_id: int
    quantity: int = Field(default=1, ge=1)

class LockResponseItem(BaseModel):
    id: int
    product_id: int
    store_id: int
    quantity: int
    status: str
    ttl_seconds: int
    expires_at: datetime
    product_name: str | None = None
    store_name: str | None = None
    unit_price: int | None = None
    image_url: str | None = None
    class Config:
        from_attributes = True

class StoreResponse(BaseModel):
    store_id: int
    place_id: str | None = None
    name: str
    category: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    phone: str | None = None
    rating: float | None = None
    class Config:
        from_attributes = True

# --- Search ---
class SearchResult(BaseModel):
    stores: list[StoreResponse] = []
    products: list[ProductResponse] = []

# --- Order / Checkout ---
class OrderCreate(BaseModel):
    product_id: int
    store_id: int
    lock_id: int
    quantity: int = Field(default=1, ge=1)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=9, max_length=20)
    address: str = Field(min_length=1, max_length=500)

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


class PaymentWebhook(BaseModel):
    provider: str = "vietqr_mock"
    order_code: str
    amount: int = Field(ge=0)
    status: Literal["paid", "failed", "cancelled"]
    transaction_id: str = Field(min_length=3, max_length=120)
    idempotency_key: str | None = Field(default=None, max_length=120)
    signature: str | None = None


class PaymentWebhookResponse(BaseModel):
    order_id: int
    order_code: str
    order_status: str
    payment_status: str
    idempotent: bool = False
