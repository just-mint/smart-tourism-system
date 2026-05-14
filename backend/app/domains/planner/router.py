"""
AEGIS Planner Domain — Router
POST /api/v1/planner/generate — Endpoint chính tạo lộ trình tối ưu O2O.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domains.planner import schema, service

router = APIRouter()


@router.post("/generate", response_model=schema.PlannerResponse)
async def generate_itinerary(
    request: schema.PlannerRequest,
    db: Session = Depends(get_db),
):
    """
    🧠 AEGIS Smart Planner — Luồng Tự Động 6 Bước.
    
    Nhận nhu cầu khách hàng (tọa độ, bán kính, keywords) →
    Tự động: Lọc PostGIS → Chấm điểm MCDM → TSP tối ưu lộ trình →
    Gắn sản phẩm O2O → Trả về lộ trình hoàn chỉnh.
    """
    try:
        return await service.generate_smart_itinerary(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Planner: {str(e)}")
