"""
AEGIS Optimization Service — MCDM Ranking Module
Min-Max Normalization trên 3 tiêu chí: Rating, Price, Distance.

[v2] Context-Aware: Áp dụng Time + Weather adjustments lên raw_rating
TRƯỚC khi chuẩn hóa Min-Max, đảm bảo context thực sự ảnh hưởng thứ hạng.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from optimization_service.core.algorithms.context_analyzer import (
    apply_context_adjustment,
)

logger = logging.getLogger(__name__)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách Haversine (km) giữa hai tọa độ."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _minmax_normalize(values: list[float]) -> list[float]:
    """Chuẩn hóa danh sách về [0, 1]. Nếu tất cả bằng nhau → 0.5."""
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    return [(v - mn) / (mx - mn) for v in values]


def rank_items(
    shops: list[dict[str, Any]],
    user_lat: float,
    user_lon: float,
    weights: dict[str, float],
    time_context: dict[str, Any] | None = None,
    weather_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Chấm điểm và xếp hạng các shop bằng MCDM Min-Max có nhận thức ngữ cảnh.

    Pipeline:
      1. Tính khoảng cách Haversine từ user đến mỗi shop
      2. [v2] Tính context_delta (time + weather) → cộng vào raw_rating
      3. Min-Max chuẩn hóa 3 chiều: rating_adjusted, price (nghịch), distance (nghịch)
      4. Weighted sum → final_score
      5. Sort DESC

    Args:
        shops:          List of shop dicts với keys: id, name, coords, price, rating, category
        user_lat/lon:   Tọa độ xuất phát
        weights:        {rating: float, distance: float, price: float} — tổng = 1.0
        time_context:   Output từ analyze_time_context(), None = không điều chỉnh
        weather_context: Output từ analyze_weather_context(), None = không điều chỉnh

    Returns:
        Danh sách shops đã được sort, mỗi item có thêm:
          - final_score (0-1)
          - distance_km
          - context_delta (để debug/log)
    """
    if not shops:
        return []

    # Fallback context objects nếu không được truyền vào
    if time_context is None:
        time_context = {"slot": "none", "rules": {}, "description": "No time context"}
    if weather_context is None:
        weather_context = {
            "outdoor_penalty": 0.0,
            "indoor_boost": 0.0,
            "condition": "Unknown",
            "temperature": None,
            "reason": "No weather context",
        }

    slot = time_context.get("slot", "none")
    weather_cond = weather_context.get("condition", "Unknown")
    logger.info(
        f"[Ranking] Chấm điểm {len(shops)} shops | time_slot={slot} | weather={weather_cond}"
    )

    # ── Bước 1: Tính khoảng cách + context delta ──
    distances: list[float] = []
    raw_ratings: list[float] = []  # Chưa adjust
    adjusted_ratings: list[float] = []  # Sau khi cộng context delta
    prices: list[float] = []
    deltas: list[float] = []

    for shop in shops:
        c = shop.get("coords", {})
        lat = c.get("lat", 0.0)
        lng = c.get("lng", 0.0)
        dist_km = haversine(user_lat, user_lon, lat, lng)
        distances.append(dist_km)

        raw_r = float(shop.get("rating", 3.0))
        raw_ratings.append(raw_r)

        prices.append(float(shop.get("price", 0.0)))

        # ── [v2] CONTEXT ADJUSTMENT ──
        delta = apply_context_adjustment(shop, time_context, weather_context)
        deltas.append(delta)

        # Cộng delta vào rating, giữ trong [0, 10] để không bị âm vô nghĩa
        adj_r = max(0.0, min(10.0, raw_r + delta))
        adjusted_ratings.append(adj_r)

    # ── Bước 2: Min-Max chuẩn hóa ──
    norm_rating = _minmax_normalize(adjusted_ratings)  # Cao = tốt
    norm_price = _minmax_normalize(prices)  # Thấp = tốt → đảo
    norm_dist = _minmax_normalize(distances)  # Gần = tốt → đảo

    norm_price_inv = [1.0 - v for v in norm_price]
    norm_dist_inv = [1.0 - v for v in norm_dist]

    # ── Bước 3: Weighted Sum ──
    w_r = weights.get("rating", 0.4)
    w_d = weights.get("distance", 0.3)
    w_p = weights.get("price", 0.3)

    # Chuẩn hóa weights tổng = 1 phòng trường hợp user nhập sai
    total_w = w_r + w_d + w_p
    if total_w > 0:
        w_r, w_d, w_p = w_r / total_w, w_d / total_w, w_p / total_w

    scored = []
    for i, shop in enumerate(shops):
        final = w_r * norm_rating[i] + w_d * norm_dist_inv[i] + w_p * norm_price_inv[i]
        scored.append(
            {
                **shop,
                "final_score": round(final, 4),
                "distance_km": round(distances[i], 2),
                "raw_rating": round(raw_ratings[i], 2),
                "context_delta": round(deltas[i], 2),
                "adjusted_rating": round(adjusted_ratings[i], 2),
            }
        )

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    # [v2] Bring anchor to the front regardless of score
    anchors = [s for s in scored if s.get("is_anchor")]
    others = [s for s in scored if not s.get("is_anchor")]
    scored = anchors + others

    # Log top 3 để debug
    for item in scored[:3]:
        logger.info(
            f"[Ranking] #{scored.index(item) + 1} '{item['name']}' | "
            f"score={item['final_score']} | raw_rating={item['raw_rating']} | "
            f"ctx_delta={item['context_delta']:+.2f} | adj_rating={item['adjusted_rating']} | "
            f"dist={item['distance_km']}km"
        )

    return scored
