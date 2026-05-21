from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

# Tạo engine SQLAlchemy thuần — đọc URI từ settings (được build từ .env)
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,  # Tự ping lại nếu kết nối bị ngắt
    pool_size=10,  # Số connection tối đa trong pool
    max_overflow=20,  # Cho phép mở thêm ngoài pool khi cao điểm
)

# Factory tạo Session — autocommit=False để kiểm soát transaction thủ công
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class cho tất cả SQLAlchemy ORM models trong các domain
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency: Cấp phát DB Session cho mỗi request,
    đảm bảo session được đóng dù có lỗi hay không (finally block).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
