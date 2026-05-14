"""
AEGIS Optimization Service — API Endpoint
POST /api/v1/optimize
Nhận danh sách shops thô → Trả về danh sách đã xếp hạng + tối ưu lộ trình.
"""

from fastapi import APIRouter, HTTPException
import logging

from optimization_service.schemas.payload import OptimizeRequest, OptimizeResponse
from optimization_service.services.optimizer import optimize_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_route(request: OptimizeRequest):
    """
    Endpoint chính của Optimization Service.
    Nhận raw shops + weights → Trả về reordered_shops + metrics.
    """
    try:
        if not request.shops:
            raise HTTPException(status_code=400, detail="Danh sách shops không được rỗng")
        
        result = optimize_pipeline(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Optimize] Lỗi pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi tối ưu hóa: {str(e)}")
