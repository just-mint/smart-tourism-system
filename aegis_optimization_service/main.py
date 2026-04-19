import uvicorn
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Aegis Optimization Microservice (DDD Framework)",
    description="Dịch vụ xử lý Thuật toán Ranking (Min-Max Scaler) & Tối ưu Lộ trình TSP (OSRM + 2-Opt).",
    version="2.0.0" # Đánh phiên bản thế hệ mới
)

# Nhúng endpoint routing vào Core
app.include_router(router)

@app.get("/")
def health_check():
    return {
        "status": "Khoẻ mạnh", 
        "microservice": "aegis_optimization_service",
        "description": "Lõi Thuật toán đã hoạt động độc quyền qua kiến trúc DDD (Port 8001)"
    }

if __name__ == "__main__":
    # Chạy trên vòng lặp độc lập không dính tới hệ thống lõi
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
