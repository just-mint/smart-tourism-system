"""
AEGIS Optimization Service — Optimizer Orchestrator
Điều phối logic: Context Analysis → Ranking → Slice Top N → TSP → Route Geometry → Metrics.

[v2] Tự động gọi Context Analyzer dựa trên raw fields (local_hour, weather_condition).
"""

import logging
from typing import Any

from optimization_service.core.algorithms.context_analyzer import (
    analyze_time_context,
    analyze_weather_context,
)
from optimization_service.core.algorithms.ranking import rank_items
from optimization_service.core.algorithms.tsp_solver import run_tsp_pipeline
from optimization_service.schemas.payload import (
    MetricsResponse,
    OptimizeRequest,
    OptimizeResponse,
    OptimizeResponseData,
    RouteGeometry,
)

logger = logging.getLogger(__name__)


def optimize_pipeline(request: OptimizeRequest) -> OptimizeResponse:
    """
    Pipeline chính: Context → Ranking → Top N → TSP → OSRM Route Geometry → Response.
    """
    # 1. Convert Pydantic → dict
    shops_raw: list[dict[str, Any]] = [
        {
            "id": shop.id,
            "name": shop.name,
            "coords": {"lat": shop.coords.lat, "lng": shop.coords.lng},
            "price": shop.price,
            "rating": shop.rating,
            "category": shop.category,
            "is_anchor": shop.is_anchor,
        }
        for shop in request.shops
    ]

    weights = {
        "rating": request.weights.rating,
        "distance": request.weights.distance,
        "price": request.weights.price,
    }

    # 2. [v2] THỰC THI PHÂN TÍCH NGỮ CẢNH (Intelligence Layer)
    time_ctx = None
    if request.local_hour is not None:
        time_ctx = analyze_time_context(request.local_hour)

    weather_ctx = None
    if request.weather_condition:
        weather_ctx = analyze_weather_context(
            request.weather_condition, request.weather_temp
        )

    logger.info(
        f"[Optimizer] Nhận {len(shops_raw)} shops. Context: Hour={request.local_hour}, Weather={request.weather_condition}"
    )

    # 3. Ranking MCDM + Context Adjustments
    ranked = rank_items(
        shops=shops_raw,
        user_lat=request.user_lat,
        user_lon=request.user_lng,
        weights=weights,
        time_context=time_ctx,
        weather_context=weather_ctx,
    )

    # 4. Slice Top N
    top_n = min(request.top_n, len(ranked))
    top_shops = ranked[:top_n]

    # 5. TSP Pipeline
    ordered_shops, metrics, route_geometry = run_tsp_pipeline(
        shops=top_shops,
        user_lat=request.user_lat,
        user_lon=request.user_lng,
    )

    # 6. Đóng gói response
    geo_obj = None
    if route_geometry and route_geometry.get("geojson"):
        geo_obj = RouteGeometry(
            geojson=route_geometry["geojson"],
            duration_minutes=route_geometry.get("duration_minutes"),
        )

    return OptimizeResponse(
        status="success",
        data=OptimizeResponseData(
            reordered_shops=ordered_shops,
            metrics=MetricsResponse(**metrics),
            route_geometry=geo_obj,
        ),
    )
