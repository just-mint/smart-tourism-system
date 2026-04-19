<div align="center">
  <h1>PHẦN E: AEGIS OPTIMIZATION MICROSERVICE</h1>
  <p><i>Tài liệu Kỹ thuật Tích hợp & Vận hành (Integration & Operations Manual)</i></p>
</div>

---

## 1. KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

Dịch vụ này được xây dựng trên triết lý **Domain-Driven Design (DDD)**. Bằng cách phân định ranh giới rõ ràng, phần lõi thuật toán (Domain Logic) hoàn toàn không bị ô nhiễm bởi các tác vụ giao tiếp Web (API Framework) hay truy vấn cơ sở dữ liệu.

Sơ đồ cấu trúc cây thư mục:
```text
aegis_optimization_service/
├── app/
│   ├── api/                 # Giao diện lập trình (API Interface): Chứa các Router mở cổng kết nối REST để giao tiếp với hệ thống bên ngoài.
│   ├── core/
│   │   └── algorithms/      # Lõi giải thuật (Core Algorithms): Nơi xử lý trực tiếp nghiệp vụ toán học, không phụ thuộc Framework Web.
│   ├── schemas/             # Định dạng dữ liệu (Data Contracts): Sử dụng Pydantic để Validate chặt chẽ Payload/Response.
│   └── services/            # Điều phối (Service Layer): Bộ xử lý trung gian kết nối API request với thư viện giải thuật.
├── main.py                  # Điểm khởi chạy của FastAPI Server (Cổng 8001).
├── main_test.py             # Script kiểm thử độc lập qua Terminal.
```

---

## 2. CHI TIẾT THUẬT TOÁN (ALGORITHM DEEP-DIVE)

### A. Hệ thống Xếp hạng (Ranking System)
Việc sử dụng các công thức cộng trừ tuyến tính truyền thống là thiếu chính xác do sự khác biệt về phương sai giữa các tập dữ liệu. Hệ thống áp dụng **Min-Max Scaler** để chuẩn hóa ma trận đa biến (Rating, Price, Distance) về không gian tham chiếu chuẩn `[0.0, 1.0]`.

*   **Tập dữ liệu Tỷ lệ thuận (Rating)**: Đạt giá trị `1.0` khi ở mức tối đa.
*   **Tập dữ liệu Tỷ lệ nghịch (Price, Distance)**: Đã được thiết kế theo cơ chế nghịch đảo (Inverse Scaler), sao cho Giá cả hoặc Khoảng cách càng thấp thì điểm chuẩn hóa lại càng tiệm cận giá trị `1.0`.

Hệ thống tính toán **Weighted Score** thông qua một hàm tuyến tính hội tụ linh hoạt nhằm đảm bảo tính công bằng toán học, tránh tình trạng một tham số có biên độ dao động lớn triệt tiêu sức ảnh hưởng của các tham số nhỏ hơn:
```text
Final_Score = w1 * Norm(Rating) + w2 * Norm_Inverse(Distance) + w3 * Norm_Inverse(Price)
```

### B. Bộ Tối ưu Lộ trình (TSP Optimizer)
Thuật toán tìm đường không sử dụng heuristic thô sơ, mà triển khai một Pipeline luân chuyển qua 3 giai đoạn:
1.  **Khởi tạo Ma trận (OSRM Table API):** Gọi tới nền tảng bản đồ giao thông nhằm thu thập *Distance Matrix* (Ma trận khoảng cách M x M) qua những cung đường thực tế. Điều này triệt tiêu ngay từ đầu phần sai số của "đường chim bay".
2.  **Dò đường sơ khởi (Greedy / Nearest Neighbor):** Hình thành một tập nghiệm ban đầu có khả năng chấp nhận được bằng cách lướt qua đồ thị theo những cạnh có chi phí di chuyển lân cận thấp nhất.
3.  **Hội tụ Tối ưu (2-Opt Edge Swapping):** Tung tổ hợp vòng lặp cắt cạnh. Thuật toán liên tiếp lặp lại quá trình bốc 2 đoạn giao cắt trên đồ thị (Intersecting lines) và hoán vị đảo chiều chúng (Reverse Slice Algorythm) cho đến lúc không còn tổ hợp đảo chiều nào mang lại cự ly nhỏ gọn hơn. Lúc này hệ thống đạt Cực Tiểu Địa Phương (Local Optima).

**Cơ chế Dung Lỗi Hệ thống (Fault Tolerance):**
Một điểm chokepoint nguy hiểm là OSRM Network có thể sập hoặc Time-out. Khi sự cố xảy ra, cơ chế Fallback ngay lập tức kích hoạt mã C-Level (Haversine Formula) tự tính ma trận không gian bề mặt địa cầu cục bộ, bảo vệ độ bền vững hệ thống không bao giờ Crash.

---

## 3. QUY CHUẨN CODE (CODING STANDARDS)

Để đảm bảo khả năng mở rộng đa người tham gia, mã nguồn tuân thủ:
*   **Quy tắc Đặt tên (Naming Rules):** Sử dụng `snake_case` thuần tuý cho toàn bộ biến và hàm (`user_lat`, `calculate_tour_distance`). Đối với Model hoặc Entity Class, sử dụng `PascalCase` (`OptimizationRequest`, `RankingAlgorithm`).
*   **Nghiêm Ngặt Định Kiểu (Type Hinting):** Các function, method bắt buộc phải có chú thích Type đầy đủ trong parameters và return type (`def optimize(path: list) -> float:`). Điều này nhằm ngăn chặn các bẫy Runtime rác, giúp Developer dễ dàng Debug.

---

## 4. TÀI LIỆU TÍCH HỢP (INTEGRATION GUIDE FOR MEMBER F)

> Chú ý cấu trúc Array Schema bên dưới để khởi tạo HTTP Request tiêu chuẩn.

| Endpoint Tiêu Chuẩn | Method | Vai trò Nghiệp Vụ |
| :--- | :--- | :--- |
| `/api/v1/optimize/` | `POST` | Cỗ máy Tối ưu Thuật toán Lõi (Nạp Danh sách Shop + Location, Trả về Tuyến Đường + Ranking) |

### 📥 Request Payload (JSON Mẫu Đầu Vào)
```json
{
  "user_lat": 10.7769,
  "user_lon": 106.7009,
  "top_n": 3,
  "w_rating": 0.4,
  "w_distance": 0.3,
  "w_price": 0.3,
  "shops": [
    {
      "id": 1,
      "name": "Cửa hàng A (Chợ Bến Thành)",
      "lat": 10.772622,
      "lon": 106.697172,
      "price": 50000,
      "rating": 4.5,
      "distance_to_user": 1.2
    },
    {
      "id": 2,
      "name": "Cửa hàng B (Nhà thờ Đức Bà)",
      "lat": 10.779722,
      "lon": 106.699172,
      "price": 40000,
      "rating": 4.8,
      "distance_to_user": 2.5
    }
  ]
}
```

### 📤 Response Format (JSON Mẫu Đầu Ra)
```json
{
  "total_input_shops": 2,
  "selected_shops": [
    {
      "id": 2,
      "name": "Cửa hàng B (Nhà thờ Đức Bà)",
      "lat": 10.779722,
      "lon": 106.699172,
      "price": 40000.0,
      "rating": 4.8,
      "distance_to_user": 2.5,
      "score_metadata": {
        "norm_rating": 1.0,
        "norm_distance": 0.0,
        "norm_price": 1.0
      },
      "final_score": 0.7338
    }
  ],
  "greedy_distance_meters": 3500.5,
  "optimized_distance_meters": 2800.5,
  "optimized_order_ids": [2, 1]
}
```
*Frontend Rendering: Sử dụng mảng `optimized_order_ids` để hiển thị lộ trình Map Map trên UI App.*

---

## 5. HƯỚNG DẪN VẬN HÀNH (OPERATIONAL MANUAL)

**A. Chuẩn bị Môi trường Máy chủ**
Kéo dải phụ thuộc Microservice `(Python >= 3.9)`:
```bash
pip install fastapi uvicorn pydantic httpx
```

**B. Kiểm thử Kỹ thuật Số Trị Toán Học (Test Độc lập)**
Lệnh này bỏ qua tầng giao tiếp Network Application, khởi tạo Sandbox Test môi trường Terminal In-Output nhằm trực tiếp đánh giá độ hội tụ và hiệu suất cắt góc đường giao chéo của thuật toán `TSP 2-Opt`:
```bash
python main_test.py
```

**C. Khởi động Microservice Trực chiến (Production/Stage Server)**
Lệnh này kích hoạt Uvicorn Server lắng nghe liên tục tại Cổng riêng biệt `8001`, sẵn sàng đón Requests Data từ Backend Core Platform (Giao thức Inter-Process Communication):
```bash
uvicorn main:app --port 8001 --reload
```
> Để kiểm tra xem Service Node đã up online hay chưa, truy xuất Giao diện Data Mappers Swagger Document tại UI Address: `http://localhost:8001/docs`
```
