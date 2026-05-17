"""
inventory/schema.py — [13.3] Merchant/Catalog management schemas.

Phân tầng schema:
  - *Create / Update*  → dùng để nhận dữ liệu từ client (POST/PUT).
  - *Response / Public* → dùng để trả về (GET).
  - Faceted search       → SearchFacets + FacetedSearchResult.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, field_validator, model_validator


# ════════════════════════════════════════════════════════════
#  ProductCategory
# ════════════════════════════════════════════════════════════

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon_url: Optional[str] = None
    sort_order: int = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon_url: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
#  Store
# ════════════════════════════════════════════════════════════

class StoreCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    phone: Optional[str] = None
    image_url: Optional[str] = None
    opening_hours: Optional[dict[str, Any]] = None   # {"mon":{"open":"08:00","close":"22:00"},...}
    service_radius: Optional[int] = 2000             # metres

    @model_validator(mode="after")
    def check_coords(self) -> "StoreCreate":
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat và lon phải được cung cấp cùng nhau")
        return self

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    phone: Optional[str] = None
    image_url: Optional[str] = None
    opening_hours: Optional[dict[str, Any]] = None
    service_radius: Optional[int] = None
    is_active: Optional[bool] = None

class StoreResponse(BaseModel):
    store_id: int
    place_id: Optional[str] = None
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    owner_id: Optional[Any] = None
    is_active: bool = True
    opening_hours: Optional[dict[str, Any]] = None
    service_radius: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Phiên bản đầy đủ hơn dùng trong Admin / Merchant Dashboard
class StoreDetailResponse(StoreResponse):
    pass


# ════════════════════════════════════════════════════════════
#  Product
# ════════════════════════════════════════════════════════════

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sku: Optional[str] = None
    price: int = 0
    original_price: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None

    @field_validator("price")
    @classmethod
    def price_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Giá không được âm")
        return v

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[int] = None
    original_price: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    product_id: int
    name: str
    price: float
    original_price: Optional[int] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    is_active: bool = True
    stock: Optional[int] = 0
    store_id: Optional[int] = None
    store_price: Optional[int] = None       # giá tại cửa hàng cụ thể (nếu có)
    is_available: bool = True
    embedding_status: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
#  Inventory / Store-Product link
# ════════════════════════════════════════════════════════════

class InventoryUpsert(BaseModel):
    """Thêm / cập nhật sản phẩm trong cửa hàng (kể cả giá riêng, stock)."""
    product_id: int
    stock: int = 0
    store_price: Optional[int] = None   # None → dùng Product.price
    is_available: bool = True

class InventoryResponse(BaseModel):
    inventory_id: int
    store_id: int
    product_id: int
    stock: int
    locked_stock: int
    store_price: Optional[int] = None
    is_available: bool = True
    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
#  Faceted Search
# ════════════════════════════════════════════════════════════

class SearchFacets(BaseModel):
    """Tham số filter cho /inventory/search."""
    q: str = ""
    category_id: Optional[int] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    # Lọc theo khoảng cách (cần lat/lon)
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius: Optional[int] = 5000        # metres, default 5 km
    # Chỉ trả về sản phẩm còn hàng
    in_stock_only: bool = False
    # Sắp xếp: "price_asc" | "price_desc" | "distance" | "relevance"
    sort: str = "relevance"
    page: int = 1
    page_size: int = 20

class FacetedProductResult(BaseModel):
    product_id: int
    name: str
    price: int                      # effective price (store_price or product.price)
    original_price: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    tags: Optional[str] = None
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    stock: int = 0
    is_available: bool = True
    distance_m: Optional[float] = None   # distance from (lat, lon) if provided

class FacetedSearchResult(BaseModel):
    stores: list[StoreResponse] = []
    products: list[FacetedProductResult] = []
    total_products: int = 0
    page: int = 1
    page_size: int = 20


# ════════════════════════════════════════════════════════════
#  Legacy schemas (kept for backwards compat)
# ════════════════════════════════════════════════════════════

class SearchResult(BaseModel):
    stores: list[StoreResponse] = []
    products: list[ProductResponse] = []

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
