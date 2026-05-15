"""
DEPRECATED — Không dùng trong production.

Domain tables hiện được quản lý bởi Alembic:
    Revision: b3c7e9f1a2d4_create_domain_tables.py

Để khởi tạo schema, chạy:
    alembic upgrade head

Script này chỉ giữ lại cho mục đích tham khảo / local dev nhanh.
"""
import sys

if __name__ == "__main__":
    print(
        "WARNING: create_domain_tables.py đã bị deprecated.\n"
        "Dùng: alembic upgrade head\n"
        "Xem: backend/app/alembic/versions/b3c7e9f1a2d4_create_domain_tables.py"
    )
    sys.exit(1)
