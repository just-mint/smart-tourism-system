from datetime import datetime, timezone, timedelta
from app.db.session import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, ForeignKey, Numeric, Text, Index
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry

def get_expire_time():
    return datetime.now(timezone.utc) + timedelta(minutes=15)

class Store(Base):
    __tablename__ = "stores"
    store_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    place_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lon: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    geom = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3,1), nullable=True)

class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, default=0)
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(512), nullable=True)
    # [v2] Thuộc tính sản phẩm — phục vụ lọc cá nhân hóa
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)     # S, M, L, XL, Free
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)    # Đỏ, Xanh, Trắng
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)           # "giá tốt,gần du lịch,quà"
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class Inventory(Base):
    __tablename__ = "inventory"
    inventory_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.store_id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)

class InventoryLock(Base):
    __tablename__ = "inventory_locks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_expire_time)
    status: Mapped[str] = mapped_column(String(50), default="soft_locked") 

    __table_args__ = (
        Index("idx_active_locks", expires_at, postgresql_where=(text("status IN ('soft_locked', 'active')"))),
    )

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
