"""
AEGIS Optimization Service — API Endpoint
POST /api/v1/optimize
Nhận danh sách shops thô → Trả về danh sách đã xếp hạng + tối ưu lộ trình.
"""

import logging
import os

from fastapi import APIRouter, Header, HTTPException
from starlette.concurrency import run_in_threadpool

from optimization_service.schemas.payload import OptimizeRequest, OptimizeResponse
from optimization_service.services.optimizer import optimize_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_route(
    request: OptimizeRequest,
    x_internal_secret: str | None = Header(None),
):
    """
    Endpoint chính của Optimization Service.
    Nhận raw shops + weights → Trả về reordered_shops + metrics.
    """
    try:
        expected_secret = os.getenv("INTERNAL_SECRET_KEY", "")
        if expected_secret and x_internal_secret != expected_secret:
            raise HTTPException(status_code=403, detail="Invalid internal secret")
        if not request.shops:
            raise HTTPException(
                status_code=400, detail="Danh sách shops không được rỗng"
            )
        if len(request.shops) > 50:
            raise HTTPException(status_code=413, detail="Tối đa 50 shops mỗi request")

        result = await run_in_threadpool(optimize_pipeline, request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Optimize] Lỗi pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi tối ưu hóa: {str(e)}")
