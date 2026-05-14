"""
AEGIS Planner Domain — Pydantic Schemas
Request/Response cho POST /api/v1/planner/generate
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


class WeightConfig(BaseModel):
    """Bộ trọng số cho thuật toán Ranking MCDM."""
    rating: float = Field(default=0.4, ge=0, le=1, description="Trọng số đánh giá sao")
    distance: float = Field(default=0.3, ge=0, le=1, description="Trọng số khoảng cách")
    price: float = Field(default=0.3, ge=0, le=1, description="Trọng số giá cả")


class PlannerRequest(BaseModel):
    """
    Input từ Frontend (Bước 1).
    """
    current_lat: float = Field(..., description="Vĩ độ hiện tại của khách")
    current_lon: float = Field(..., description="Kinh độ hiện tại của khách")
    radius: int = Field(default=2000, ge=500, le=50000, description="Bán kính tìm kiếm (mét)")
    keywords: str = Field(default="", description="Từ khóa tìm kiếm (vd: cafe, lụa, nón lá)")
    weights: WeightConfig = WeightConfig()
    top_n: int = Field(default=5, ge=1, le=10, description="Số lượng điểm đến tối ưu")
    # [v2] Context-aware: Frontend có thể gửi local_hour (0-23), nếu không có Backend tự lấy
    local_hour: Optional[int] = Field(
        default=None, ge=0, le=23,
        description="Giờ địa phương của khách (0-23). Nếu không gửi, hệ thống tự xác định theo UTC+7."
    )
    max_budget: Optional[int] = Field(
        default=None, ge=0,
        description="Ngân sách tối đa (VNĐ). Nếu không gửi, không giới hạn ngân sách."
    )


class ProductInRoute(BaseModel):
    """Sản phẩm gắn vào mỗi điểm dừng trong lộ trình."""
    product_id: int
    name: str
    price: float
    image_url: Optional[str] = None


class StopInRoute(BaseModel):
    """Một điểm dừng trong lộ trình tối ưu."""
    order: int
    store_id: Optional[int] = None
    place_db_id: Optional[int] = None
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lon: float
    rating: Optional[float] = None
    distance_km: Optional[float] = None
    final_score: Optional[float] = None
    products: list[ProductInRoute] = []


class RouteGeometry(BaseModel):
    """GeoJSON geometry từ OSRM Route API — LineString đường thực tế."""
    geojson: dict      # {type: "LineString", coordinates: [[lon,lat], ...]}
    duration_minutes: Optional[float] = None


class RouteMetrics(BaseModel):
    """Số liệu tổng hợp của lộ trình."""
    total_price: float
    total_distance_km: float
    routing_fallback_used: bool


class WeatherInfo(BaseModel):
    """Thông tin thời tiết tại vị trí xuất phát."""
    temperature: Optional[float] = None
    condition: Optional[str] = None
    code: Optional[int] = None


class ContextInfo(BaseModel):
    """Thông tin ngữ cảnh đã được áp dụng — để hiển thị trên UI."""
    time_slot: str = "none"          # morning / evening / ...
    time_description: str = ""
    weather_condition: str = "Unknown"
    weather_reason: str = ""
    hour_used: int = 12


class PlannerResponse(BaseModel):
    """
    Output hoàn chỉnh trả về Frontend (Bước 2-4 kết hợp).
    """
    status: str = "success"
    optimized_route: list[StopInRoute]
    metrics: RouteMetrics
    route_geometry: Optional[RouteGeometry] = None  # GeoJSON LineString đường thực tế
    weather: Optional[WeatherInfo] = None
    context_applied: Optional[ContextInfo] = None   # [v2] Ngữ cảnh đã can thiệp
    total_candidates: int = Field(default=0, description="Tổng số ứng viên thô trước khi lọc")
