-- Script khởi tạo PostgreSQL chạy tự động khi container lần đầu tiên boot
-- Kích hoạt các Extension cần thiết cho AEGIS

-- 1. PostGIS cho Spatial queries (bắt buộc cho domain Spatial)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. pgvector cho AI Vector Embeddings (bắt buộc cho domain Vision - VirtualCloset)
-- Migration sẽ FAIL nếu thiếu lệnh này
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. pg_trgm cho Full-text Search nhanh trên bảng 1.7M dòng (khuyến nghị)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

<<<<<<< Updated upstream
-- 4. uuid-ossp cho việc tự động tạo UUID
=======
-- 4. uuid-ossp
>>>>>>> Stashed changes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 5. Thông báo hoàn tất
SELECT 'AEGIS Database Extensions initialized successfully' AS status;
