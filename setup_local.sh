#!/bin/bash

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}==================================================================${NC}"
echo -e "${RED}❌ SCRIPT ĐÃ BỊ DEPRECATED (VÔ HIỆU HOÁ) ❌${NC}"
echo -e "${YELLOW}Dự án hiện tại đã chuyển sang quản trị Database bằng Alembic.${NC}"
echo -e "${YELLOW}File 'travel_app_full_data.sql' chứa cấu trúc và dữ liệu cũ (ví dụ user_id là integer),${NC}"
echo -e "${YELLOW}điều này gây xung đột (conflict) nghiêm trọng với schema chuẩn mới (UUID).${NC}"
echo -e "${YELLOW}==================================================================${NC}"
echo ""
echo -e "${GREEN}👉 CÁCH SETUP MỚI CHUẨN NHẤT:${NC}"
echo -e "1. Xoá DB cũ bị lỗi: docker compose down -v"
echo -e "2. Bật DB mới: docker compose up -d db"
echo -e "3. Chạy Alembic (trong thư mục backend): uv run alembic upgrade head"
echo -e "4. Khởi động API và nạp dữ liệu bằng tay hoặc API Seeder (nếu có)."
exit 1
