"""
AEGIS Optimization Service — Pydantic Schemas (DTOs)
Validation nghiêm ngặt cho Request/Response của endpoint /api/v1/optimize.
"""

from typing import Any

from pydantic import BaseModel, Field


class ShopCoords(BaseModel):
    lat: float
    lng: float


class ShopItem(BaseModel):
    id: str
    name: str
    coords: ShopCoords
    price: float = 0
    rating: float = 0
    category: str | None = None  # Cần cho context-aware ranking
    is_anchor: bool = False


class WeightConfig(BaseModel):
    rating: float = Field(default=0.4, ge=0, le=1)
    distance: float = Field(default=0.3, ge=0, le=1)
    price: float = Field(default=0.3, ge=0, le=1)


class TimeContext(BaseModel):
    """Ngữ cảnh thời gian — từ analyze_time_context()."""

    slot: str = "none"  # morning / lunch / afternoon / evening / night
    hour: int = 12
    rules: dict[str, float] = {}  # {category: delta}
    description: str = ""


class WeatherContext(BaseModel):
    """Ngữ cảnh thời tiết — từ analyze_weather_context()."""

    outdoor_penalty: float = 0.0
    indoor_boost: float = 0.0
    condition: str = "Unknown"  # Rainy / Clear / Cloudy / Storm
    temperature: float | None = None
    reason: str = ""


class OptimizeRequest(BaseModel):
    """
    Request payload cho POST /api/v1/optimize.
    Cần có tọa độ user, danh sách shop thô, bộ trọng số, và dữ liệu ngữ cảnh thô.
    """

    user_lat: float
    user_lng: float
    weights: WeightConfig = WeightConfig()
    shops: list[ShopItem]
    top_n: int = Field(
        default=5, ge=1, le=20, description="Số lượng shops tốt nhất sau khi rank"
    )

    # [v2] Raw Context Fields — Đơn giản hóa cho caller
    local_hour: int | None = None
    weather_condition: str | None = None  # Rainy, Clear, etc.
    weather_temp: float | None = None


class MetricsResponse(BaseModel):
    total_price: float
    total_distance_km: float
    routing_fallback_used: bool


class RouteGeometry(BaseModel):
    geojson: dict[str, Any]  # GeoJSON LineString từ OSRM Route API
    duration_minutes: float | None = None


class OptimizeResponseData(BaseModel):
    reordered_shops: list[dict[str, Any]]
    metrics: MetricsResponse
    route_geometry: RouteGeometry | None = None  # None = OSRM không khả dụng


class OptimizeResponse(BaseModel):
    """
    Response format chuẩn của Optimization Service.
    """

    status: str = "success"
    data: OptimizeResponseData
