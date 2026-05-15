import os
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
import logging

from optimization_service.api.v1.optimize import router as optimize_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# --- BẢO MẬT: Khởi tạo Internal Token Check ---
INTERNAL_TOKEN = os.getenv("INTERNAL_AUTH_TOKEN")
if not INTERNAL_TOKEN:
    raise RuntimeError("INTERNAL_AUTH_TOKEN chưa được set trong environment!")
api_key_header = APIKeyHeader(name="X-Internal-Token", auto_error=True)

async def verify_internal_token(api_key: str = Security(api_key_header)):
    if api_key != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Internal Service Token")
    return api_key
# ---------------------------------------------

app = FastAPI(
    title="AEGIS Optimization Service",
    description="Microservice nội bộ xử lý Ranking và TSP. Không public ra ngoài.",
    version="2.0.0",
)

# Chỉ định rõ nguồn gọi nội bộ, không dùng ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://backend:8000"], # Domain của Core Backend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn Dependency kiểm tra Token vào toàn bộ Router này
app.include_router(
    optimize_router, 
    prefix="/api/v1", 
    tags=["optimize"], 
    dependencies=[Depends(verify_internal_token)]
)

@app.get("/", tags=["health"])
def health_check():
    return {"status": "operational", "service": "Internal Optimization"}