#!/usr/bin/env bash
set -e

echo "🚀 Bắt đầu cài đặt môi trường Local cho AEGIS O2O..."

# 1. Setup .env file
if [ ! -f .env ]; then
    echo "📄 Tạo file .env từ .env.example..."
    cp .env.example .env
    # Replace placeholder with a default password for local dev
    sed -i.bak 's/<generate-a-secure-random-string-here>/changethis/g' .env
    rm -f .env.bak
    echo "✅ Đã tạo file .env với mật khẩu mặc định (changethis)."
else
    echo "✅ File .env đã tồn tại, bỏ qua bước tạo mới."
fi

# 2. Build and start Docker containers
echo "🐳 Đang khởi động Docker Compose (quá trình này có thể mất vài phút lần đầu)..."
docker compose up -d --build

# Wait for DB to be healthy
echo "⏳ Đang chờ Database khởi động hoàn tất..."
sleep 15 # Allow postgres to initialize

# 3. Chạy Migration và Seed data cơ bản
echo "🛠️ Đang chạy Database Migrations..."
docker compose exec -T backend uv run alembic upgrade head

echo "🌱 Đang nạp dữ liệu quản trị (Admin User)..."
docker compose exec -T backend uv run python app/initial_data.py

echo "📦 Đang nạp dữ liệu Sản phẩm và Cửa hàng mẫu..."
docker compose exec -T backend uv run python scripts/seed_stores.py

echo "✅ CÀI ĐẶT HOÀN TẤT!"
echo "----------------------------------------------------"
echo "🌐 Frontend (Giao diện Web): http://localhost:5173"
echo "⚙️ Backend API:            http://localhost:8000/docs"
echo "👑 Admin Account:          admin@example.com / changethis"
echo "----------------------------------------------------"
echo "Để xem log hệ thống, chạy lệnh: docker compose logs -f"
