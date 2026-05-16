"""
AEGIS Optimization Service — FastAPI Entrypoint
Khởi chạy: uvicorn optimization_service.main:app --port 8001 --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from optimization_service.api.v1.optimize import router as optimize_router

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app = FastAPI(
    title="AEGIS Optimization Service",
    description="Microservice chuyên biệt xử lý Ranking (MCDM) và TSP (Tối ưu lộ trình) cho hệ thống O2O.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — cho phép Core Backend gọi qua
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký router
app.include_router(optimize_router, prefix="/api/v1", tags=["optimize"])


@app.get("/", tags=["health"])
def health_check():
    return {
        "service": "AEGIS Optimization Service",
        "status": "operational",
        "version": "2.0.0",
        "endpoints": ["/api/v1/optimize", "/docs"],
    }
