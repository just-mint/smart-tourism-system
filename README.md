# AEGIS O2O

AEGIS O2O (Online-to-Offline) is a modern full-stack application designed for high-performance spatial and inventory management.

## 🚀 Technology Stack

- **Backend**: FastAPI, SQLModel, PostgreSQL (with PostGIS & pgvector extensions), Redis, Celery.
- **Frontend**: React, Vite, Tailwind CSS, shadcn/ui, TanStack Query, TanStack Router.
- **Infrastructure**: Docker Compose, Traefik, Adminer.

---

## 🚀 Dành cho Developer mới (Hướng dẫn Setup)

Đồng đội clone code về hãy làm theo 4 bước sau để môi trường có đủ bảng và dữ liệu thật:

**Bước 1:** Clone code về máy
```bash
git clone <repository_url> aegis-o2o
cd aegis-o2o
```

**Bước 2:** Cấu hình biến môi trường
Copy file `.env.example` thành `.env` (tại thư mục gốc hoặc `backend/`) và điền thông tin Database PostgreSQL của bạn.

**Bước 3:** Chạy DB và nạp toàn bộ Dữ Liệu
Chạy script dưới đây. Kịch bản này sẽ tự động bật Database Container (qua Docker) và nạp toàn bộ cấu trúc bảng, dữ liệu mẫu, vector AI từ file `travel_app_full_data.sql`:
```bash
bash setup_local.sh
```
> **Lưu ý:** Bạn cần phải cài đặt Docker và bật Docker Desktop trước khi chạy lệnh này.

**Bước 4:** Tạo môi trường ảo (venv) và chạy ứng dụng
Sau khi Database đã có đủ dữ liệu, bạn chỉ việc cài môi trường và chạy code:
```bash
# 1. Tạo và kích hoạt venv
python -m venv venv
source venv/bin/activate  # (Trên Windows dùng: venv\Scripts\activate)

# 2. Cài đặt thư viện Backend
cd backend
pip install -r requirements.txt  # Hoặc: uv sync
uv run fastapi dev app/main.py   # Chạy Backend ở localhost:8000
```
```bash
# 3. Mở tab Terminal khác cho Frontend
cd frontend
bun install
bun run dev                      # Chạy Frontend ở localhost:5173
```

---

## 🛠️ How To Run the Project

You can run the project either fully containerized via Docker (easiest), or natively on your local machine for active development.

### Option 1: Running with Docker Compose (Recommended)

To start the entire stack (Database, Backend, Frontend, and Traefik Proxy), use:

```bash
docker compose watch
```

Once the containers are up and running, you can access the services at:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database Adminer**: http://localhost:8080
- **Traefik UI**: http://localhost:8090

> **Note:** The first time you start the stack, it might take a minute for the database to initialize and the backend migrations to run. You can view logs with `docker compose logs -f backend`.

### Option 2: Running Locally (Native Development)

If you prefer to run the application processes natively on your machine (e.g., Ubuntu), follow these steps:

#### 1. Start the Database Infrastructure
First, start only the database container:
```bash
docker compose up -d db
```

#### 2. Start the Backend
The backend uses `uv` for lightning-fast dependency management.

```bash
cd backend

# Install dependencies
uv sync

# Run the FastAPI development server
uv run fastapi dev app/main.py
```
*(The backend will be available at http://localhost:8000)*

#### 3. Start the Frontend
The frontend uses `bun` for package management.

```bash
cd frontend

# Install dependencies
bun install

# Start the Vite development server
bun run dev
```
*(The frontend will be available at http://localhost:5173)*

---

## 📚 Further Documentation

For more detailed information, please refer to the following documents:
- **Backend Guide**: [backend/README.md](./backend/README.md)
- **Frontend Guide**: [frontend/README.md](./frontend/README.md)
- **Advanced Development & Docker**: [development.md](./development.md)
- **Deployment Instructions**: [deployment.md](./deployment.md)

## 🧠 AEGIS Optimization Service (Week 2 Core)

### 1. 🏗 TỔNG QUAN & KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

**Vai trò trong hệ sinh thái AEGIS O2O:**
**AEGIS Optimization Service** là một Microservice độc lập chuyên biệt chịu trách nhiệm giải quyết hai bài toán nặng về tính toán nhất của nền tảng:
1. **Multi-Criteria Decision Making (MCDM):** Đánh giá và xếp hạng cửa hàng (Ranking).
2. **Traveling Salesperson Problem (TSP):** Tối ưu hóa lộ trình di chuyển (Routing).

Bằng cách tách rời logic này, chúng ta đảm bảo **Core Server** không bị nghẽn (bottleneck) khi phải xử lý các tính toán ma trận OSRM phức tạp.

**Tech Stack:**
- **Framework:** FastAPI
- **Validation:** Pydantic
- **Language:** Python 3.10+
- **Routing Engine:** OSRM (Open Source Routing Machine)

**Triết lý Domain-Driven Design (DDD):**
Dự án áp dụng chặt chẽ kiến trúc DDD nhằm phân tách ranh giới giữa giao thức mạng (API) và lõi thuật toán nghiệp vụ (Core Algorithms).

```text
aegis_optimization_service/
├── api/                   # Controller Layer: Định tuyến các endpoints
│   └── v1/
│       └── optimize.py    # Endpoint POST /api/v1/optimize
├── core/                  # Domain Layer: Chứa não bộ thuật toán
│   └── algorithms/
│       ├── ranking.py     # MCDM, Min-Max Scaler
│       └── tsp_solver.py  # Greedy, 2-Opt, Haversine Fallback
├── schemas/               # Data Transfer Objects (Pydantic Models)
│   └── payload.py         # Request/Response schemas validation
├── services/              # Application Layer: Điều phối logic giữa API & Core
│   └── optimizer.py       # Orchestrator gom Ranking & TSP
├── main.py                # Điểm khởi chạy FastAPI (App Entrypoint)
├── main_test.py           # Kịch bản test nội bộ (Unit/Integration Test)
└── requirements.txt       # Danh sách dependencies
```

### 2. 🧠 CHI TIẾT LÕI THUẬT TOÁN (CORE ALGORITHMS - CẬP NHẬT TUẦN 2)

- **Ranking System (MCDM):** Hệ thống sử dụng thuật toán Đa tiêu chí, áp dụng **Min-Max Scaler** để đưa các thang đo (Rating, Price, Distance) về dải `[0, 1]`. Khoảng cách đã được **THAM SỐ HÓA**, nhận động `user_lat` và `user_lon` từ request API để tính toán real-time, thay vì fix cứng.
- **TSP Optimizer (Tối ưu lộ trình):** Luồng xử lý qua 3 bước: Lấy OSRM Matrix -> Tìm Nearest Neighbor (Greedy) -> Tối ưu 2-Opt. Hàm `reorder_shops` giúp trả về danh sách cửa hàng thực tế (Dict objects) thay vì Index vô nghĩa.
- **Tính toán Chi phí:** Hàm `calculate_total_metrics` tự động tính toán tổng `total_price` và `total_distance_km` từ lộ trình chốt.
- **Cơ chế Fallback Sinh Tồn:** OSRM public API có thể bị timeout. Hệ thống đã tích hợp sẵn cơ chế tự động chuyển sang công thức **Haversine** (Đường chim bay) nếu OSRM lỗi, đảm bảo hệ thống luôn trả về lộ trình mà không bị crash.

### 3. 💻 HƯỚNG DẪN VẬN HÀNH DÀNH CHO TEAM (LOCAL SETUP & RUN)

**Bước 1:** Clone repo và checkout nhánh.
```bash
git clone <repository_url> aegis_optimization_service
cd aegis_optimization_service
git checkout develop
```

**Bước 2:** Cài đặt môi trường.
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Bước 3:** Chạy kịch bản test nội bộ (để kiểm tra Fallback Haversine).
```bash
python main_test.py
```

**Bước 4:** Khởi động server.
```bash
uvicorn main:app --port 8001 --reload
```

### 4. 🔌 TÀI LIỆU TÍCH HỢP API (INTEGRATION GUIDE FOR MEMBER F)

- **Endpoint:** `POST /api/v1/optimize`
- **Request Payload mẫu (JSON):** Cần có tọa độ user (`user_lat`, `user_lng`), danh sách shop thô (`shops`) lấy từ `data.json`, và bộ trọng số `weights`.

```json
{
  "user_lat": 10.7720,
  "user_lng": 106.6983,
  "weights": {
    "rating": 0.4,
    "distance": 0.3,
    "price": 0.3
  },
  "shops": [
    {
      "id": "tour_1",
      "name": "Nón Lá Việt Traditional",
      "coords": {"lat": 10.7720, "lng": 106.6983},
      "price": 85000,
      "rating": 4.6
    }
  ]
}
```

- **Response Format mẫu (JSON):** Phải thể hiện rõ danh sách shop đã được sắp xếp (`reordered_shops`) và trường `metrics` chứa tổng giá/quãng đường dự kiến.

```json
{
  "status": "success",
  "data": {
    "reordered_shops": [ ... ],
    "metrics": {
      "total_price": 85000,
      "total_distance_km": 0.0,
      "routing_fallback_used": false
    }
  }
}
```

---

## 📄 License
This project is licensed under the terms of the MIT license.
