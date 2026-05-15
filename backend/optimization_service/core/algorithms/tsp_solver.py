"""
AEGIS Optimization Service — TSP Solver Module
Traveling Salesperson Problem: Greedy Nearest Neighbor → 2-Opt Improvement.

Lộ trình:
  1. Lấy OSRM Distance Matrix (NxN) — format CHUẨN: lon,lat;lon,lat
  2. Nearest Neighbor (Greedy) tìm lộ trình ban đầu
  3. 2-Opt cải thiện — swap các đoạn đường
  4. Fetch OSRM Route geometry thực tế theo thứ tự tối ưu
  5. Fallback: Haversine nếu OSRM timeout/lỗi hoàn toàn
"""

import math
import logging
import os
from typing import Any

import httpx
import asyncio

logger = logging.getLogger(__name__)

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
OSRM_TIMEOUT = 10.0  # Tăng lên 10s để tránh lỗi mạng ngắn hạn


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách Haversine (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _build_osrm_coord_str(coords: list[tuple[float, float]]) -> str:
    """
    ⚠️ LUẬT THÉP OSRM: BẮT BUỘC format là lon,lat (KHÔNG phải lat,lon).
    coords: list of (lat, lon) — đảo thành lon,lat khi ghép URL.
    """
    return ";".join(f"{lon},{lat}" for lat, lon in coords)


def _build_haversine_matrix(coords: list[tuple[float, float]]) -> list[list[float]]:
    """
    Xây dựng distance matrix NxN bằng Haversine (fallback khi OSRM lỗi hoàn toàn).
    coords: list of (lat, lon)
    """
    n = len(coords)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


async def _fetch_osrm_matrix(coords: list[tuple[float, float]]) -> list[list[float]] | None:
    if len(coords) < 2:
        return None

    coord_str = _build_osrm_coord_str(coords)
    url = f"{OSRM_BASE_URL}/table/v1/driving/{coord_str}"

    try:
        # DÙNG ASYNC CLIENT
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"[TSP] OSRM Table trả mã {response.status_code}")
                return None
            data = response.json()
            # ... (Giữ nguyên logic parse json cũ của bạn)
            raw = data.get("durations")
            return [[float(cell) if cell is not None else 9999.0 for cell in row] for row in raw]
            
    except httpx.TimeoutException:
        logger.warning(f"[TSP] OSRM Table timeout sau {OSRM_TIMEOUT}s")
        return None
    except Exception as e:
        logger.warning(f"[TSP] OSRM Table lỗi: {e}")
        return None

async def _fetch_osrm_route_geometry(ordered_coords: list[tuple[float, float]]) -> dict | None:
    if len(ordered_coords) < 2:
        return None

    coord_str = _build_osrm_coord_str(ordered_coords)
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coord_str}?overview=full&geometries=geojson"

    try:
        # DÙNG ASYNC CLIENT
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            data = response.json()
            # ... (Giữ nguyên logic parse json cũ của bạn)
            route = data.get("routes", [])[0]
            return {
                "geojson": route.get("geometry"),
                "distance_km": round(route.get("distance", 0) / 1000, 2),
                "duration_minutes": round(route.get("duration", 0) / 60, 1),
            }
    except Exception as e:
        logger.warning(f"[TSP] OSRM Route lỗi: {e}")
        return None

def _nearest_neighbor(matrix: list[list[float]], start: int = 0) -> list[int]:
    """Greedy Nearest Neighbor — tìm lộ trình ban đầu."""
    n = len(matrix)
    visited = [False] * n
    tour = [start]
    visited[start] = True

    for _ in range(n - 1):
        current = tour[-1]
        nearest = -1
        nearest_dist = float("inf")
        for j in range(n):
            if not visited[j] and matrix[current][j] < nearest_dist:
                nearest = j
                nearest_dist = matrix[current][j]
        if nearest == -1:
            break
        tour.append(nearest)
        visited[nearest] = True

    return tour


def _two_opt(tour: list[int], matrix: list[list[float]]) -> list[int]:
    """2-Opt improvement — swap các đoạn đường cho tới khi không cải thiện được nữa."""
    n = len(tour)
    improved = True
    best = tour[:]

    def _tour_cost(t: list[int]) -> float:
        return sum(matrix[t[i]][t[i + 1]] for i in range(len(t) - 1))

    best_cost = _tour_cost(best)

    max_iterations = 100
    iteration = 0
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                new_tour = best[:i] + best[i: j + 1][::-1] + best[j + 1:]
                new_cost = _tour_cost(new_tour)
                if new_cost < best_cost:
                    best = new_tour
                    best_cost = new_cost
                    improved = True

    return best


def reorder_shops(
    shops: list[dict[str, Any]], tsp_order: list[int]
) -> list[dict[str, Any]]:
    """Sắp xếp lại danh sách shops theo thứ tự TSP — trả dict thay vì index."""
    return [shops[i] for i in tsp_order if i < len(shops)]


def calculate_total_metrics(
    ordered_shops: list[dict[str, Any]],
    fallback_used: bool = False,
    osrm_distance_km: float | None = None,
) -> dict[str, Any]:
    """Tính tổng giá và tổng khoảng cách từ lộ trình đã chốt."""
    total_price = sum(shop.get("price", 0) for shop in ordered_shops)

    if osrm_distance_km is not None:
        # Ưu tiên dùng khoảng cách thực tế từ OSRM Route
        total_distance_km = osrm_distance_km
    else:
        # Fallback: Haversine chim bay
        total_distance_km = 0.0
        for i in range(len(ordered_shops) - 1):
            c1 = ordered_shops[i].get("coords", {})
            c2 = ordered_shops[i + 1].get("coords", {})
            if c1 and c2:
                d = haversine(
                    c1.get("lat", 0), c1.get("lng", 0),
                    c2.get("lat", 0), c2.get("lng", 0),
                )
                total_distance_km += d
        total_distance_km = round(total_distance_km, 2)

    return {
        "total_price": total_price,
        "total_distance_km": total_distance_km,
        "routing_fallback_used": fallback_used,
    }


async def run_tsp_pipeline(
    shops: list[dict[str, Any]],
    user_lat: float,
    user_lon: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict | None]:
    
    if not shops:
        return [], {"total_price": 0, "total_distance_km": 0, "routing_fallback_used": False}, None

    coords: list[tuple[float, float]] = [(user_lat, user_lon)]
    for shop in shops:
        c = shop.get("coords", {})
        coords.append((c.get("lat", 0.0), c.get("lng", 0.0)))

    fallback_used = False
    
    # BẮT BUỘC DÙNG AWAIT
    matrix = await _fetch_osrm_matrix(coords)
    
    if matrix is None:
        logger.info("[TSP] OSRM Table timeout/lỗi → Fallback bằng Haversine (P1-29)")
        matrix = _build_haversine_matrix(coords)
        fallback_used = True

    tour = _nearest_neighbor(matrix, start=0)
    tour = _two_opt(tour, matrix)

    shop_tour = [idx - 1 for idx in tour if idx > 0]
    ordered_shops = reorder_shops(shops, shop_tour)

    ordered_coords: list[tuple[float, float]] = [(user_lat, user_lon)]
    for shop in ordered_shops:
        c = shop.get("coords", {})
        ordered_coords.append((c.get("lat", 0.0), c.get("lng", 0.0)))

    # BẮT BUỘC DÙNG AWAIT
    route_info = await _fetch_osrm_route_geometry(ordered_coords)

    if route_info:
        osrm_distance_km = route_info.get("distance_km")
        route_geometry = {
            "geojson": route_info["geojson"],
            "duration_minutes": route_info.get("duration_minutes"),
        }
    else:
        # Fallback Haversine cho geometry nếu OSRM Route cũng sập
        osrm_distance_km = None
        route_geometry = None
        fallback_used = True

    metrics = calculate_total_metrics(ordered_shops, fallback_used, osrm_distance_km)

    return ordered_shops, metrics, route_geometry