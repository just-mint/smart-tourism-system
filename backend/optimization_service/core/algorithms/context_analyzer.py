"""
AEGIS Optimization Service — Context Analyzer
Phân tích ngữ cảnh thời gian + thời tiết để điều chỉnh điểm ranking.

Hai nguồn ngữ cảnh:
  1. TIME CONTEXT  — Giờ trong ngày → xác định loại địa điểm phù hợp
  2. WEATHER CONTEXT — Điều kiện thời tiết → penalty outdoor / boost indoor
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CẤU HÌNH NGỮ CẢNH THỜI GIAN
# ─────────────────────────────────────────────────────────────────────────────

# Các "slot" thời gian trong ngày
TIME_SLOTS = {
    "morning":   (6,  11),   # 06:00 – 10:59
    "lunch":     (11, 14),   # 11:00 – 13:59
    "afternoon": (14, 18),   # 14:00 – 17:59
    "evening":   (18, 22),   # 18:00 – 21:59
    "night":     (22, 6),    # 22:00 – 05:59 (vượt nửa đêm)
}

# Boost / penalty của từng category theo time slot
# Giá trị dương = boost (cộng thêm vào rating trước Min-Max)
# Giá trị âm = penalty
TIME_CATEGORY_RULES: dict[str, dict[str, float]] = {
    "morning": {
        "cafe":        +1.5,
        "coffee":      +1.5,
        "breakfast":   +1.5,
        "museum":      +1.0,
        "park":        +1.0,
        "market":      +0.8,
        "bar":         -2.0,
        "pub":         -2.0,
        "night_market": -3.0,
        "club":        -3.0,
    },
    "lunch": {
        "restaurant":  +2.0,
        "food":        +1.5,
        "indoor":      +0.8,
        "mall":        +0.5,
        "museum":      +0.3,
        "outdoor":     -0.5,
    },
    "afternoon": {
        "mall":        +1.0,
        "indoor":      +0.8,
        "cafe":        +0.8,
        "museum":      +0.5,
        "outdoor":     +0.3,
    },
    "evening": {
        "restaurant":  +1.5,
        "food":        +1.2,
        "night_market": +3.0,
        "bar":         +2.5,
        "pub":         +2.5,
        "club":        +2.0,
        "shopping":    +1.0,
        "museum":      -3.0,   # Đóng cửa 17-18h
        "park":        -1.5,
    },
    "night": {
        "night_market": +3.0,
        "bar":         +3.0,
        "pub":         +3.0,
        "club":        +2.5,
        "restaurant":  +1.0,
        "museum":      -5.0,   # Đóng cửa hoàn toàn
        "park":        -3.0,
        "cafe":        -1.0,
        "market":      -1.0,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# CẤU HÌNH NGỮ CẢNH THỜI TIẾT
# ─────────────────────────────────────────────────────────────────────────────

OUTDOOR_CATEGORIES = {"outdoor", "park", "nature", "beach", "garden", "monument"}
INDOOR_CATEGORIES  = {"indoor", "mall", "cafe", "coffee", "museum", "gallery",
                       "restaurant", "food", "bar", "club", "shopping"}


def _get_time_slot(hour: int) -> str:
    """Trả về time slot name dựa vào giờ (0-23)."""
    if 6 <= hour < 11:
        return "morning"
    elif 11 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def analyze_time_context(hour: int) -> dict[str, Any]:
    """
    Phân tích ngữ cảnh thời gian.

    Args:
        hour: Giờ hiện tại (0-23) theo múi giờ địa phương

    Returns:
        dict gồm:
          - slot: tên khoảng thời gian
          - rules: {category: delta_score}
          - description: mô tả ngắn
    """
    slot = _get_time_slot(hour)
    rules = TIME_CATEGORY_RULES.get(slot, {})

    descriptions = {
        "morning":   "Buổi sáng — ưu tiên café, bảo tàng, công viên",
        "lunch":     "Buổi trưa — ưu tiên nhà hàng, địa điểm trong nhà",
        "afternoon": "Buổi chiều — ưu tiên trung tâm thương mại, café",
        "evening":   "Buổi tối — ưu tiên chợ đêm, quán bar, nhà hàng",
        "night":     "Đêm khuya — ưu tiên chợ đêm, bar; tắt bảo tàng/công viên",
    }

    logger.info(f"[Context] Giờ {hour}h → Slot: {slot} | Áp dụng {len(rules)} quy tắc")
    return {
        "slot": slot,
        "rules": rules,
        "hour": hour,
        "description": descriptions.get(slot, ""),
    }


def analyze_weather_context(condition: str, temperature: float | None) -> dict[str, Any]:
    """
    Phân tích ngữ cảnh thời tiết.

    Args:
        condition: "Rainy" | "Storm" | "Cloudy" | "Clear" | "Unknown"
        temperature: nhiệt độ Celsius

    Returns:
        dict gồm:
          - outdoor_penalty: điểm trừ cho category outdoor
          - indoor_boost: điểm cộng cho category indoor
          - reason: mô tả lý do
    """
    outdoor_penalty = 0.0
    indoor_boost = 0.0
    reason = "Thời tiết bình thường, không điều chỉnh."

    if condition in ("Rainy", "Storm"):
        outdoor_penalty = -2.0
        indoor_boost = +1.5
        reason = f"Trời {condition} → phạt outdoor, thưởng indoor."

    elif temperature is not None and temperature > 35:
        outdoor_penalty = -1.5
        indoor_boost = +1.2
        reason = f"Nhiệt độ {temperature}°C > 35°C → ưu tiên địa điểm có máy lạnh."

    elif condition == "Cloudy":
        # Thời tiết nhiều mây — outdoor vẫn ok, không phạt
        outdoor_penalty = 0.0
        indoor_boost = 0.0
        reason = "Trời nhiều mây, không điều chỉnh."

    logger.info(f"[Context] Thời tiết: {condition} / {temperature}°C → {reason}")
    return {
        "outdoor_penalty": outdoor_penalty,
        "indoor_boost": indoor_boost,
        "condition": condition,
        "temperature": temperature,
        "reason": reason,
    }


def _normalize_category(cat: str | None) -> str:
    """Chuẩn hóa category string về lowercase, strip."""
    return (cat or "").lower().strip()


def apply_context_adjustment(
    shop: dict[str, Any],
    time_ctx: dict[str, Any],
    weather_ctx: dict[str, Any],
) -> float:
    """
    Tính tổng điều chỉnh ngữ cảnh (delta) cho một shop.

    Quy trình:
      1. Khớp category của shop với time_rules → cộng/trừ
      2. Khớp category với outdoor/indoor lists → áp dụng weather penalty/boost

    Returns:
        delta: số điểm điều chỉnh (có thể âm)
    """
    delta = 0.0
    raw_cat = _normalize_category(shop.get("category"))
    tags: set[str] = set()

    # Tách category có thể là "cafe, outdoor" hoặc "indoor mall"
    for part in raw_cat.replace(",", " ").split():
        tags.add(part)

    # ── 1. TIME RULES ──
    time_rules: dict[str, float] = time_ctx.get("rules", {})
    for tag in tags:
        if tag in time_rules:
            adjustment = time_rules[tag]
            delta += adjustment
            logger.debug(f"[Context] Shop '{shop.get('name')}' tag='{tag}' time_adj={adjustment:+.1f}")

    # ── 2. WEATHER RULES ──
    outdoor_penalty: float = weather_ctx.get("outdoor_penalty", 0.0)
    indoor_boost: float = weather_ctx.get("indoor_boost", 0.0)

    is_outdoor = bool(tags & OUTDOOR_CATEGORIES)
    is_indoor = bool(tags & INDOOR_CATEGORIES)

    if is_outdoor and outdoor_penalty != 0.0:
        delta += outdoor_penalty
        logger.debug(f"[Context] Shop '{shop.get('name')}' outdoor→ weather_penalty={outdoor_penalty:+.1f}")

    if is_indoor and indoor_boost != 0.0:
        delta += indoor_boost
        logger.debug(f"[Context] Shop '{shop.get('name')}' indoor → weather_boost={indoor_boost:+.1f}")

    return delta
