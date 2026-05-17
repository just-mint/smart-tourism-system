from datetime import datetime, timezone
from app.db.session import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Numeric, Text,
    Index, UniqueConstraint, CheckConstraint, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import text
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry


# ── [13.3] ProductCategory ────────────────────────────────────────────────────
class ProductCategory(Base):
    """Danh mục sản phẩm chuẩn hoá — dùng cho faceted search & filter."""
    __tablename__ = "product_categories"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)   # ví dụ: "ao-thun"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ── [13.3] Store ──────────────────────────────────────────────────────────────
class Store(Base):
    __tablename__ = "stores"
    store_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    place_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)        # [13.3]
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lon: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    geom = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)          # [13.3]
    # [13.3] Merchant / ownership
    owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)              # [13.3]
    # [13.3] Opening hours — JSONB, ví dụ:
    # { "mon": {"open":"08:00","close":"22:00"}, "tue": {...}, ..., "sun": {...}, "holiday_closed": true }
    opening_hours: Mapped[dict | None] = mapped_column(JSONB, nullable=True)    # [13.3]
    # [13.3] Service radius (metres) — bán kính giao hàng / geofence
    service_radius: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2000)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ── [13.3] Product ────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)  # [13.3]
    price: Mapped[int] = mapped_column(Integer, default=0)          # giá gốc / mặc định
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [13.3] Normalized category FK
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_categories.id"), nullable=True, index=True
    )
    # [13.3] Legacy tag blob (kept for backwards compat with existing seed data)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)              # [13.3]
    # Embedding pipeline
    embedding: Mapped[list | None] = mapped_column(Vector(512), nullable=True)
    embedding_status: Mapped[str | None] = mapped_column(String(50), default="pending", nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_nonnegative'),
    )


# ── Inventory ─────────────────────────────────────────────────────────────────
class Inventory(Base):
    __tablename__ = "inventory"
    inventory_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.store_id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)
    # [13.3] Giá riêng theo cửa hàng (NULL = dùng Product.price)
    store_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # [13.3] Trạng thái bán tại cửa hàng cụ thể (hết mùa, tạm ngừng…)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint('store_id', 'product_id', name='uq_inventory_store_product'),
        CheckConstraint('stock >= 0', name='check_stock_nonnegative'),
        CheckConstraint('locked_stock >= 0', name='check_locked_stock_nonnegative'),
    )


# ── InventoryLock (unchanged) ─────────────────────────────────────────────────
class InventoryLock(Base):
    __tablename__ = "inventory_locks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="soft_locked")

    __table_args__ = (
        Index(
            "idx_active_locks",
            expires_at,
            postgresql_where=(text("status IN ('soft_locked', 'active')")),
        ),
    )


# ── Order (unchanged) ─────────────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.store_id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total_amount: Mapped[int] = mapped_column(Integer, default=0)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_SHIP")
    order_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
