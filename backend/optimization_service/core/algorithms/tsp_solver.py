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

logger = logging.getLogger(__name__)

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://osrm-backend:5000")
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


def _fetch_osrm_matrix(coords: list[tuple[float, float]]) -> list[list[float]] | None:
    """
    Gọi OSRM Table API lấy distance matrix (mét → km).

    ⚠️ OSRM public /table/v1 KHÔNG hỗ trợ ?annotations=distance → phải bỏ param đó.
    Default trả về 'durations' matrix (giây). Ta dùng durations để so sánh tương đối
    cho TSP vẫn cho kết quả đúng (đường ngắn ≈ thời gian ngắn trong cùng khu vực).
    coords: list of (lat, lon)
    Returns: matrix NxN (durations giây) hoặc None nếu lỗi.
    """
    if len(coords) < 2:
        return None

    # ⚠️ OSRM BẮT BUỘC: lon,lat — đảo từ (lat, lon) trong DB
    coord_str = _build_osrm_coord_str(coords)
    url = f"{OSRM_BASE_URL}/table/v1/driving/{coord_str}"

    try:
        with httpx.Client(timeout=OSRM_TIMEOUT) as client:
            response = client.get(url)
            if response.status_code != 200:
                logger.warning(f"[TSP] OSRM Table trả mã {response.status_code}: {response.text[:200]}")
                return None
            data = response.json()
            if data.get("code") != "Ok":
                logger.warning(f"[TSP] OSRM Table code lỗi: {data.get('code')} — {data.get('message', '')}")
                return None

            # OSRM /table trả 'durations' (giây) theo mặc định
            raw = data.get("durations")
            if not raw:
                logger.warning("[TSP] OSRM Table không có trường 'durations'")
                return None

            # Trả về duration matrix (giây) — dùng làm chi phí cho TSP
            return [[float(cell) if cell is not None else 9999.0 for cell in row] for row in raw]

    except httpx.TimeoutException:
        logger.warning(f"[TSP] OSRM Table timeout sau {OSRM_TIMEOUT}s")
        return None
    except Exception as e:
        logger.warning(f"[TSP] OSRM Table lỗi không xác định: {e}")
        return None


def _fetch_osrm_route_geometry(ordered_coords: list[tuple[float, float]]) -> dict | None:
    """
    Sau khi TSP tìm ra THỨ TỰ TỐI ƯU, gọi OSRM Route API để lấy đường
    đi THỰC TẾ uốn theo đường phố (không phải đường chim bay).

    ⚠️ OSRM BẮT BUỘC: lon,lat — đảo từ (lat, lon) trong DB.
    Returns: GeoJSON geometry object {type: "LineString", coordinates: [[lon,lat], ...]}
             hoặc None nếu lỗi.
    """
    if len(ordered_coords) < 2:
        return None

    coord_str = _build_osrm_coord_str(ordered_coords)
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coord_str}?overview=full&geometries=geojson"

    try:
        with httpx.Client(timeout=OSRM_TIMEOUT) as client:
            response = client.get(url)
            if response.status_code != 200:
                logger.warning(f"[TSP] OSRM Route trả mã {response.status_code}: {response.text[:200]}")
                return None
            data = response.json()
            if data.get("code") != "Ok":
                logger.warning(f"[TSP] OSRM Route code lỗi: {data.get('code')} — {data.get('message', '')}")
                return None

            routes = data.get("routes", [])
            if not routes:
                return None

            route = routes[0]
            geometry = route.get("geometry")  # GeoJSON LineString
            distance_m = route.get("distance", 0)
            duration_s = route.get("duration", 0)

            logger.info(f"[TSP] OSRM Route thực tế: {distance_m/1000:.2f}km, {duration_s/60:.1f} phút")
            return {
                "geojson": geometry,
                "distance_km": round(distance_m / 1000, 2),
                "duration_minutes": round(duration_s / 60, 1),
            }

    except httpx.TimeoutException:
        logger.warning(f"[TSP] OSRM Route timeout sau {OSRM_TIMEOUT}s")
        return None
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


def run_tsp_pipeline(
    shops: list[dict[str, Any]],
    user_lat: float,
    user_lon: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict | None]:
    """
    Pipeline hoàn chỉnh:
      1. OSRM Table → Duration Matrix (NxN)
      2. Nearest Neighbor → Greedy tour
      3. 2-Opt → Cải thiện thứ tự
      4. OSRM Route → Lấy geometry đường thực tế
      5. Fallback Haversine chỉ khi OSRM hoàn toàn không khả dụng

    Args:
        shops: Danh sách shops (đã được rank, thường là Top 5)
        user_lat, user_lon: Tọa độ xuất phát

    Returns:
        (ordered_shops, metrics, route_geometry)
        route_geometry: dict với 'geojson' (LineString) hoặc None
    """
    if not shops:
        return [], {"total_price": 0, "total_distance_km": 0, "routing_fallback_used": False}, None

    # Xây danh sách tọa độ: user_location (index 0) + shops
    # Lưu dưới dạng (lat, lon) — hàm _build_osrm_coord_str sẽ đảo thành lon,lat
    coords: list[tuple[float, float]] = [(user_lat, user_lon)]
    for shop in shops:
        c = shop.get("coords", {})
        coords.append((c.get("lat", 0.0), c.get("lng", 0.0)))

    # === Bước 1: OSRM Duration Matrix ===
    fallback_used = False
    matrix = _fetch_osrm_matrix(coords)
    if matrix is None:
        logger.info("[TSP] OSRM Table không khả dụng → Haversine Fallback cho TSP ordering")
        matrix = _build_haversine_matrix(coords)
        fallback_used = True

    # === Bước 2: Nearest Neighbor (bắt đầu từ index 0 = user location) ===
    tour = _nearest_neighbor(matrix, start=0)

    # === Bước 3: 2-Opt cải thiện ===
    tour = _two_opt(tour, matrix)

    # Bỏ index 0 (user location) ra khỏi tour, chỉ giữ shop indices
    shop_tour = [idx - 1 for idx in tour if idx > 0]
    ordered_shops = reorder_shops(shops, shop_tour)

    # === Bước 4: OSRM Route API → Lấy geometry đường THỰC TẾ ===
    # Thứ tự: user → shop_1 → shop_2 → ... theo tour tối ưu
    ordered_coords: list[tuple[float, float]] = [(user_lat, user_lon)]
    for shop in ordered_shops:
        c = shop.get("coords", {})
        ordered_coords.append((c.get("lat", 0.0), c.get("lng", 0.0)))

    route_info = _fetch_osrm_route_geometry(ordered_coords)

    if route_info:
        osrm_distance_km = route_info.get("distance_km")
        route_geometry = {
            "geojson": route_info["geojson"],
            "duration_minutes": route_info.get("duration_minutes"),
        }
        logger.info(f"[TSP] ✅ OSRM Route geometry thực tế: {osrm_distance_km}km")
    else:
        # OSRM Route cũng lỗi → dùng Haversine tính khoảng cách
        osrm_distance_km = None
        route_geometry = None
        fallback_used = True
        logger.warning("[TSP] ⚠️ OSRM Route không khả dụng — đường chim bay được dùng làm fallback")

    metrics = calculate_total_metrics(ordered_shops, fallback_used, osrm_distance_km)

    return ordered_shops, metrics, route_geometry
