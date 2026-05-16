"""
AEGIS Optimization Service — FastAPI Entrypoint
Khởi chạy: uvicorn optimization_service.main:app --port 8001 --reload
"""

import logging
import os

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
allowed_origins = [
    origin.strip()
    for origin in os.getenv("OPTIMIZATION_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-Internal-Secret"],
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
