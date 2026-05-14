#!/bin/bash

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==================================================================${NC}"
echo -e "${YELLOW}🚀 BẮT ĐẦU QUÁ TRÌNH SETUP DATABASE TỪ BẢN DUMP 🚀${NC}"
echo -e "${YELLOW}Đảm bảo bạn đã copy file .env.example thành .env và điền đủ thông tin.${NC}"
echo -e "${YELLOW}==================================================================${NC}"
echo ""

# Load environment variables if .env exists to extract DB info
if [ -f .env ]; then
  # Dùng export để truyền biến xuống docker compose nếu cần
  export $(grep -v '^#' .env | xargs)
else
  echo -e "${RED}LỖI: Không tìm thấy file .env ở thư mục gốc. Vui lòng copy từ .env.example.${NC}"
  exit 1
fi

POSTGRES_USER=${POSTGRES_USER:-aegis_user}
POSTGRES_DB=${POSTGRES_DB:-aegis_db}

echo -e "⏳ [1/2] Đang khởi động Database container bằng Docker..."
docker compose up -d db
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lỗi khi khởi động container db. Hãy chắc chắn bạn đã cài và mở Docker.${NC}"
    exit 1
fi

echo "⏳ Đang đợi Database sẵn sàng (chờ khoảng 10-15s)..."
# Đợi để container init, đặc biệt là lần chạy đầu
sleep 15

# Kiểm tra file dump
if [ ! -f "travel_app_full_data.sql" ]; then
    echo -e "${RED}❌ Lỗi: Không tìm thấy file 'travel_app_full_data.sql' ở thư mục gốc!${NC}"
    exit 1
fi

echo -e "\n⏳ [2/2] Đang nạp toàn bộ cấu trúc & dữ liệu từ travel_app_full_data.sql..."
echo "Quá trình này có thể mất một vài phút. Vui lòng không tắt terminal..."

docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < travel_app_full_data.sql

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lỗi trong quá trình import dữ liệu!${NC}"
    exit 1
fi

echo -e "\n${GREEN}✨ Bơm dữ liệu thành công! Database của bạn giờ đã đồng bộ hoàn toàn với bản gốc.${NC}"
echo -e "${GREEN}👉 Tiếp theo: Kích hoạt venv, cài đặt requirements và khởi động Backend/Frontend.${NC}"
