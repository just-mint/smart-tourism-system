from fastapi import APIRouter, HTTPException
from app.schemas.optimization import OptimizationRequest, OptimizationResponse
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/api/v1/optimize", tags=["Optimization Engine"])

@router.post("/", response_model=OptimizationResponse)
async def optimize_route(payload: OptimizationRequest):
    """
    Điểm truy cập Microservice:
    Đầu vào là danh sách Cửa hàng lớn và Vị trí của người dùng.
    Máy chủ sẽ trả về danh sách Cửa hàng đã được Ranking (Top N) và thứ tự truy cập ngắn nhất tính theo TSP 2-opt.
    """
    try:
        result = await OptimizationService.process_optimization(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lõi hệ thống Optimization: {str(e)}")
