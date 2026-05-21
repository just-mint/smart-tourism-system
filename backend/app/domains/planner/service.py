"""
AEGIS Planner Domain — Service Layer (Orchestrator)
"Nhạc trưởng" điều phối luồng 6 bước O2O:

  Bước 2: PostGIS quét bán kính → Raw Candidates
  Bước 3: Gọi Optimization Service → Ranked + TSP
  Bước 4: Enrich Products vào mỗi Stop

Trả về JSON hoàn chỉnh cho Frontend (Bước 5).
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.culture.model import Place
from app.domains.inventory.model import Inventory, Product, Store
from app.domains.planner.schema import (
    ContextInfo,
    PlannerRequest,
    PlannerResponse,
    ProductInRoute,
    RouteGeometry,
    RouteMetrics,
    StopInRoute,
    WeatherInfo,
)
from app.domains.spatial.service import fetch_real_weather

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fallback_metrics(
    shops: list[dict[str, Any]],
    user_lat: float,
    user_lon: float,
) -> dict[str, Any]:
    total_price = sum(float(shop.get("price") or 0) for shop in shops)
    total_distance = 0.0
    prev_lat = user_lat
    prev_lon = user_lon
    for shop in shops:
        coords = shop.get("coords", {})
        lat = float(coords.get("lat") or 0)
        lon = float(coords.get("lng") or 0)
        if lat and lon:
            total_distance += _haversine_km(prev_lat, prev_lon, lat, lon)
            prev_lat, prev_lon = lat, lon
    return {
        "total_price": total_price,
        "total_distance_km": round(total_distance, 2),
        "routing_fallback_used": True,
    }


def _query_stores_in_radius(
    db: Session,
    lat: float,
    lon: float,
    radius: int,
    keywords: str,
    max_budget: int | None = None,
) -> list[dict[str, Any]]:
    """
    Bước 2: Lọc cửa hàng bằng PostGIS ST_DWithin + keyword ILIKE.
    [v2] Bổ sung: Chỉ giữ stores CÒN HÀNG (stock > locked_stock)
                  và không vượt ngân sách (avg_price <= max_budget).
    """
    point = f"SRID=4326;POINT({lon} {lat})"

    # Base query: PostGIS proximity
    query = db.query(Store).filter(
        func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius)
    )

    # Lọc theo keyword nếu có
    if keywords and keywords.strip():
        keyword_parts = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if keyword_parts:
            keyword_filters = [Store.name.ilike(f"%{kw}%") for kw in keyword_parts]
            category_filters = [Store.category.ilike(f"%{kw}%") for kw in keyword_parts]
            query = query.filter(or_(*keyword_filters, *category_filters))

    stores = query.limit(50).all()

    results = []
    if not stores:
        return results

    store_ids = [s.store_id for s in stores]

    # [Fix P1-15] Aggregate Inventory and Product in one query
    inv_prod = (
        db.query(Inventory, Product)
        .join(Product, Inventory.product_id == Product.product_id)
        .filter(Inventory.store_id.in_(store_ids))
        .all()
    )

    store_invs = defaultdict(list)
    store_prods = defaultdict(list)

    for inv, prod in inv_prod:
        store_invs[inv.store_id].append(inv)
        store_prods[inv.store_id].append(prod)

    for s in stores:
        store_id = s.store_id
        inventory_rows = store_invs.get(store_id, [])
        products = store_prods.get(store_id, [])

        # Attractions are "experience" stops — they don't sell products
        # so they should NOT be filtered out for missing inventory.
        if s.category == "attraction":
            results.append(
                {
                    "id": str(store_id),
                    "store_id": store_id,
                    "name": s.name,
                    "coords": {
                        "lat": float(s.lat) if s.lat else 0.0,
                        "lng": float(s.lon) if s.lon else 0.0,
                    },
                    "price": 0.0,
                    "rating": float(s.rating) if s.rating else 4.0,
                    "category": s.category,
                    "address": s.address,
                }
            )
            continue

        # [v2] CHECK STOCK:
        # Nếu store không có sản phẩm nào, loại luôn vì không có gì để mua (tránh avg price = 0)
        if not inventory_rows:
            continue

        has_available = any(row.stock > row.locked_stock for row in inventory_rows)
        if not has_available:
            continue

        avg_price = sum(p.price for p in products) / len(products) if products else 0.0

        # [v2] CHECK BUDGET: Loại store vượt ngân sách
        if max_budget is not None and avg_price > max_budget:
            continue

        results.append(
            {
                "id": str(store_id),
                "store_id": store_id,
                "name": s.name,
                "coords": {
                    "lat": float(s.lat) if s.lat else 0.0,
                    "lng": float(s.lon) if s.lon else 0.0,
                },
                "price": avg_price,
                "rating": float(s.rating) if s.rating else 3.0,
                "category": s.category,
                "address": s.address,
            }
        )

    return results


async def _call_optimization_service(
    shops: list[dict], user_lat: float, user_lon: float, weights: dict, top_n: int
) -> dict[str, Any] | None:
    """
    Bước 3 & 4: Gọi Optimization Microservice (port 8001).
    Trả về {reordered_shops, metrics} hoặc None nếu lỗi.
    """
    payload = {
        "user_lat": user_lat,
        "user_lng": user_lon,
        "weights": weights,
        "shops": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "coords": s["coords"],
                "price": s["price"],
                "rating": s["rating"],
            }
            for s in shops
        ],
        "top_n": top_n,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.OPTIMIZATION_SERVICE_URL,
                json=payload,
                headers={"X-Internal-Secret": settings.INTERNAL_SECRET_KEY},
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"[Planner] Optimization Service trả mã {response.status_code}: {response.text}"
                )
                return None
    except Exception as e:
        logger.error(f"[Planner] Không thể kết nối Optimization Service: {e}")
        return None


async def generate_smart_itinerary(
    db: Session, request: PlannerRequest
) -> PlannerResponse:
    """
    Hàm chính — Orchestrate toàn bộ luồng 6 bước (phần Backend: Bước 2-4).
    [v2] Bổ sung nhận thức ngữ cảnh: Giờ (Time) và Thời tiết (Weather).
    """
    logger.info(
        f"[Planner] Bắt đầu: lat={request.current_lat}, lon={request.current_lon}, "
        f"radius={request.radius}m, keywords='{request.keywords}'"
    )

    # ── NGỮ CẢNH THỜI GIAN ──
    # Ưu tiên local_hour từ request, nếu không có tự lấy giờ Việt Nam (UTC+7)
    current_hour = request.local_hour
    if current_hour is None:
        vn_time = datetime.now(timezone(timedelta(hours=7)))
        current_hour = vn_time.hour

    # ── NGỮ CẢNH THỜI TIẾT ──
    weather_data = await fetch_real_weather(request.current_lat, request.current_lon)
    weather_cond = (
        weather_data.get("condition", "Unknown") if weather_data else "Unknown"
    )
    weather_temp = weather_data.get("temperature") if weather_data else None

    # === BƯỚC 2: Lọc cửa hàng (PostGIS + Stock + Budget) ===
    # === BƯỚC 2a: ANCHOR DESTINATION LOOKUP ===
    # If the user typed keywords (e.g. "Thảo Cầm Viên"), try to find the
    # actual Place and inject it as the mandatory first stop.
    anchor_candidate = None
    search_keywords = request.keywords
    center_lat = request.current_lat
    center_lon = request.current_lon

    if request.keywords and request.keywords.strip():
        primary_keyword = request.keywords.split(",")[0].strip()
        if primary_keyword:
            # Search Places table for the best match
            anchor_place = (
                db.query(Place)
                .filter(Place.name.ilike(f"%{primary_keyword}%"))
                .filter(Place.lat.isnot(None), Place.lon.isnot(None))
                .first()
            )
            if anchor_place:
                logger.info(
                    "[Planner] Anchor destination found: '%s' (cat=%s)",
                    anchor_place.name, anchor_place.category,
                )
                anchor_candidate = {
                    "id": str(anchor_place.id),
                    "store_id": anchor_place.id,
                    "name": anchor_place.name,
                    "coords": {
                        "lat": float(anchor_place.lat),
                        "lng": float(anchor_place.lon),
                    },
                    "price": 0.0,
                    "rating": float(anchor_place.rating) if anchor_place.rating else 4.5,
                    "category": anchor_place.category or "attraction",
                    "address": anchor_place.address,
                    "is_anchor": True,
                }
                # Center search around the anchor
                center_lat = float(anchor_place.lat)
                center_lon = float(anchor_place.lon)
                # Remove the primary keyword so we don't filter all other stores by it
                parts = [kw.strip() for kw in request.keywords.split(",")]
                search_keywords = ",".join(parts[1:]) if len(parts) > 1 else ""

    # === BƯỚC 2b: Lấy ứng viên xung quanh tâm ===
    raw_candidates = _query_stores_in_radius(
        db,
        center_lat,
        center_lon,
        request.radius,
        search_keywords,
        max_budget=request.max_budget,
    )

    if anchor_candidate:
        # Remove duplicates: if anchor is already in raw_candidates, remove it
        raw_candidates = [
            c for c in raw_candidates
            if c["name"].lower() != anchor_candidate["name"].lower()
        ]

    # === BƯỚC 2c: CATEGORY-DIVERSE SELECTION ===
    # Partition candidates by category for balanced slot allocation
    retail_categories = {"store", "clothing", "souvenir", "supermarket"}
    food_candidates = [c for c in raw_candidates if c.get("category") == "food"]
    store_candidates = [
        c for c in raw_candidates if c.get("category") in retail_categories
    ]
    attraction_candidates = [c for c in raw_candidates if c.get("category") == "attraction"]
    other_candidates = [
        c
        for c in raw_candidates
        if c.get("category") not in retail_categories | {"food", "attraction"}
    ]

    # Calculate slot allocation
    remaining_slots = request.top_n
    if anchor_candidate:
        remaining_slots -= 1  # Reserve slot 1 for anchor

    # Allocate: roughly 40% food, 30% store, 30% attraction (from remaining slots)
    food_slots = max(1, int(remaining_slots * 0.4)) if food_candidates else 0
    store_slots = max(1, int(remaining_slots * 0.3)) if store_candidates else 0
    attraction_slots = remaining_slots - food_slots - store_slots

    # Fill slots from each category (sorted by rating desc)
    food_candidates.sort(key=lambda x: x.get("rating", 0), reverse=True)
    store_candidates.sort(key=lambda x: x.get("rating", 0), reverse=True)
    attraction_candidates.sort(key=lambda x: x.get("rating", 0), reverse=True)

    diverse_candidates = []
    diverse_candidates.extend(food_candidates[:food_slots])
    diverse_candidates.extend(store_candidates[:store_slots])
    diverse_candidates.extend(attraction_candidates[:attraction_slots])
    diverse_candidates.extend(other_candidates[:max(0, remaining_slots - len(diverse_candidates))])

    # If we still don't have enough, fill from any category
    if len(diverse_candidates) < remaining_slots:
        used_ids = {c["id"] for c in diverse_candidates}
        for c in raw_candidates:
            if c["id"] not in used_ids:
                diverse_candidates.append(c)
                used_ids.add(c["id"])
            if len(diverse_candidates) >= remaining_slots:
                break

    # Prepend anchor if exists
    if anchor_candidate:
        diverse_candidates.insert(0, anchor_candidate)

    raw_candidates = diverse_candidates
    total_candidates = len(raw_candidates)

    if not raw_candidates:
        return PlannerResponse(
            status="no_results",
            optimized_route=[],
            metrics=RouteMetrics(
                total_price=0, total_distance_km=0, routing_fallback_used=False
            ),
            weather=WeatherInfo(**weather_data) if weather_data else None,
            total_candidates=0,
        )

    # === BƯỚC 3 & 4: Chấm điểm + TSP (qua Optimization Service) ===
    # TRUYỀN DỮ LIỆU NGỮ CẢNH SANG PORT 8001
    payload = {
        "user_lat": request.current_lat,
        "user_lng": request.current_lon,
        "weights": {
            "rating": request.weights.rating,
            "distance": request.weights.distance,
            "price": request.weights.price,
        },
        "shops": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "coords": s["coords"],
                "price": s["price"],
                "rating": s["rating"],
                "category": s["category"],  # Cực kỳ quan trọng để match rules
            }
            for s in raw_candidates
        ],
        "top_n": request.top_n,
        "local_hour": current_hour,
        "weather_condition": weather_cond,
        "weather_temp": weather_temp,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                settings.OPTIMIZATION_SERVICE_URL,
                json=payload,
                headers={"X-Internal-Secret": settings.INTERNAL_SECRET_KEY},
            )
            if response.status_code == 200:
                opt_result = response.json()
                reordered_shops = opt_result["data"]["reordered_shops"]
                metrics_data = opt_result["data"]["metrics"]
                geo_raw = opt_result["data"].get("route_geometry")
                route_geo = RouteGeometry(**geo_raw) if geo_raw else None
            else:
                raise Exception(f"Optimization Service Error: {response.text}")
    except Exception as e:
        logger.error(f"[Planner] Fallback do lỗi Optimization: {e}")
        raw_candidates.sort(key=lambda x: x.get("rating", 0), reverse=True)
        reordered_shops = raw_candidates[: request.top_n]
        metrics_data = _fallback_metrics(
            reordered_shops,
            request.current_lat,
            request.current_lon,
        )
        route_geo = None

    # Fetch all products for these stores at once
    reordered_store_ids = [
        shop.get("store_id") or int(shop.get("id", 0)) for shop in reordered_shops
    ]
    inv_prod_results = (
        db.query(Inventory, Product)
        .join(Product, Inventory.product_id == Product.product_id)
        .filter(Inventory.store_id.in_(reordered_store_ids))
        .all()
    )

    store_route_products = defaultdict(list)
    for inv, prod in inv_prod_results:
        if len(store_route_products[inv.store_id]) < 5:
            store_route_products[inv.store_id].append(
                ProductInRoute(
                    product_id=prod.product_id,
                    name=prod.name,
                    price=prod.price,
                    image_url=prod.image_url,
                )
            )

    # === ENRICH & PACKING ===
    optimized_route: list[StopInRoute] = []
    for idx, shop in enumerate(reordered_shops):
        store_id = shop.get("store_id") or int(shop.get("id", 0))
        products = store_route_products.get(store_id, [])
        coords = shop.get("coords", {})

        stop = StopInRoute(
            order=idx + 1,
            store_id=store_id,
            name=shop.get("name", ""),
            category=shop.get("category"),
            address=shop.get("address"),
            lat=coords.get("lat", 0),
            lon=coords.get("lng", 0),
            rating=shop.get("rating"),
            distance_km=shop.get("distance_km"),
            final_score=shop.get("final_score"),
            products=products,
        )
        optimized_route.append(stop)

    # Tạo ContextApplied info để Frontend hiển thị
    # Mapping đơn giản mô tả slot
    time_desc = "Đang tối ưu theo thời gian thực"
    if 6 <= current_hour < 11:
        time_desc = "Buổi sáng — Ưu tiên khởi đầu năng lượng"
    elif 11 <= current_hour < 14:
        time_desc = "Giờ nghỉ trưa — Ưu tiên ẩm thực & trong nhà"
    elif 18 <= current_hour < 22:
        time_desc = "Buổi tối — Khám phá ẩm thực & giải trí"

    ctx_info = ContextInfo(
        time_slot="active",  # Hoặc map theo slot thực
        time_description=time_desc,
        weather_condition=weather_cond,
        weather_reason=f"Đã điều chỉnh gợi ý theo điều kiện {weather_cond}",
        hour_used=current_hour,
    )

    return PlannerResponse(
        status="success",
        optimized_route=optimized_route,
        metrics=RouteMetrics(**metrics_data),
        route_geometry=route_geo,
        weather=WeatherInfo(**weather_data) if weather_data else None,
        context_applied=ctx_info,
        total_candidates=total_candidates,
    )
