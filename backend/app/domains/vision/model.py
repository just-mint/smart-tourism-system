from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VisionTask(Base):
    __tablename__ = "vision_tasks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    image_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(50), default="processing")
    detected_objects: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    matched_product_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class VirtualCloset(Base):
    __tablename__ = "virtual_closets"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), index=True)
    image_path: Mapped[str] = mapped_column(String(1000))
    # Nhờ cài đặt hệ xịn pgvector, lưu mảng Embedings 512D rất mạnh
    vector_embedding: Mapped[list | None] = mapped_column(Vector(512), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
