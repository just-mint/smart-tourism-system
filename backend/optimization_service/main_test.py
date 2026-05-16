"""
AEGIS Optimization Service — Unit & Integration Tests
Chạy: python -m optimization_service.main_test (từ thư mục backend/)
"""

import logging

from optimization_service.core.algorithms.ranking import haversine, rank_items
from optimization_service.core.algorithms.tsp_solver import (
    run_tsp_pipeline,
)
from optimization_service.schemas.payload import (
    OptimizeRequest,
    ShopCoords,
    ShopItem,
    WeightConfig,
)
from optimization_service.services.optimizer import optimize_pipeline

logger = logging.getLogger(__name__)


def test_haversine():
    """Test Haversine: HCM → Hà Nội ≈ 1,138 km"""
    d = haversine(10.7769, 106.7009, 21.0285, 105.8542)
    assert 1100 < d < 1200, f"Haversine sai: {d}km"
    logger.info("Haversine HCM→HN = %.1fkm", d)


def test_ranking():
    """Test ranking MCDM với 3 shops"""
    shops = [
        {"id": "1", "name": "Shop A", "coords": {"lat": 10.7720, "lng": 106.6983}, "price": 50000, "rating": 4.5},
        {"id": "2", "name": "Shop B", "coords": {"lat": 10.7800, "lng": 106.7000}, "price": 150000, "rating": 3.0},
        {"id": "3", "name": "Shop C", "coords": {"lat": 10.7750, "lng": 106.6950}, "price": 80000, "rating": 4.8},
    ]
    result = rank_items(shops, user_lat=10.7720, user_lon=106.6983, weights={"rating": 0.4, "distance": 0.3, "price": 0.3})
    assert len(result) == 3
    # Shop có rating cao + gần + giá rẻ nên xếp trước
    logger.info("Ranking: %s", [(s["name"], s["final_score"]) for s in result])


def test_tsp_pipeline():
    """Test TSP pipeline (dùng OSRM thật, fallback Haversine nếu lỗi)"""
    shops = [
        {"id": "1", "name": "Điểm 1", "coords": {"lat": 10.780, "lng": 106.690}, "price": 50000, "rating": 4.0},
        {"id": "2", "name": "Điểm 2", "coords": {"lat": 10.770, "lng": 106.700}, "price": 60000, "rating": 4.2},
        {"id": "3", "name": "Điểm 3", "coords": {"lat": 10.775, "lng": 106.695}, "price": 70000, "rating": 3.8},
    ]
    ordered, metrics, route_geometry = run_tsp_pipeline(shops, user_lat=10.772, user_lon=106.698)
    assert len(ordered) == 3
    assert metrics["total_distance_km"] >= 0
    has_geo = route_geometry is not None and route_geometry.get("geojson") is not None
    logger.info(
        "TSP Pipeline: order=%s, distance=%skm, fallback=%s, has_osrm_geo=%s",
        [s["name"] for s in ordered],
        metrics["total_distance_km"],
        metrics["routing_fallback_used"],
        has_geo,
    )


def test_full_pipeline():
    """Test full optimize_pipeline()"""
    request = OptimizeRequest(
        user_lat=10.7720,
        user_lng=106.6983,
        weights=WeightConfig(rating=0.4, distance=0.3, price=0.3),
        shops=[
            ShopItem(id="tour_1", name="Nón Lá Việt Traditional", coords=ShopCoords(lat=10.7720, lng=106.6983), price=85000, rating=4.6),
            ShopItem(id="tour_2", name="Café Sài Gòn Heritage", coords=ShopCoords(lat=10.7780, lng=106.7020), price=120000, rating=4.2),
            ShopItem(id="tour_3", name="Áo Dài Phương", coords=ShopCoords(lat=10.7750, lng=106.6950), price=350000, rating=4.8),
            ShopItem(id="tour_4", name="Bến Thành Souvenir", coords=ShopCoords(lat=10.7725, lng=106.6980), price=65000, rating=3.9),
            ShopItem(id="tour_5", name="Lụa Tơ Tằm Artisan", coords=ShopCoords(lat=10.7700, lng=106.7010), price=280000, rating=4.5),
        ],
        top_n=5,
    )
    result = optimize_pipeline(request)
    assert result.status == "success"
    assert len(result.data.reordered_shops) <= 5
    assert result.data.metrics.total_distance_km >= 0
    logger.info(
        "Full Pipeline: %s shops, distance=%skm",
        len(result.data.reordered_shops),
        result.data.metrics.total_distance_km,
    )
    logger.info("Thứ tự: %s", [s["name"] for s in result.data.reordered_shops])
    logger.info(
        "Metrics: price=%s, fallback=%s",
        result.data.metrics.total_price,
        result.data.metrics.routing_fallback_used,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("AEGIS Optimization Service — Test Suite")

    test_haversine()
    test_ranking()
    test_tsp_pipeline()
    test_full_pipeline()

    logger.info("ALL TESTS PASSED")
