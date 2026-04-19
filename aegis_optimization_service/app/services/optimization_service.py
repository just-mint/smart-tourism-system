from app.core.algorithms.ranking_algo import RankingAlgorithm
from app.core.algorithms.tsp_solver import TSPSolver

class OptimizationService:
    @staticmethod
    async def process_optimization(payload):
        # Chuyển đổi Pydantic schemas (List[ShopItem]) thành danh sách các dictionary
        shop_dicts = [s.model_dump() for s in payload.shops]
        
        # 1. Pipeline Ranking: Trích xuất và phân quyền đánh giá bằng user_lat, user_lon
        top_shops = RankingAlgorithm.rank_items(
            items=shop_dicts, 
            user_lat=payload.user_lat,
            user_lon=payload.user_lon,
            w1=payload.w_rating, 
            w2=payload.w_distance, 
            w3=payload.w_price
        )[:payload.top_n]
        
        if not top_shops:
            raise ValueError("Hệ thống lọc không có shop nào thoả mãn!")
            
        # 2. Bóc tách Nested Object coords {"lat": x, "lng": y} đưa vào pipeline định tuyến OSRM
        user_coord = (payload.user_lon, payload.user_lat) 
        shop_coords = [(s['coords']['lng'], s['coords']['lat']) for s in top_shops]
        
        # 3. Kích hoạt Pipeline Tối ưu Lộ trình OSRM Table + 2-Opt TSP
        tsp_result = await TSPSolver.run_tsp_pipeline(user_coord, shop_coords)
        
        # 4. Trích xuất Output Mapping
        opt_indexes = tsp_result["opt_path_indexes"]
        
        ordered_shop_ids = []
        for idx in opt_indexes:
            if idx == 0: continue # Skip User location origin
            shop = top_shops[idx - 1] # Index 1-based alignment back to 0-based index
            ordered_shop_ids.append(shop['id'])
            
        return {
            "total_input_shops": len(payload.shops),
            "selected_shops": top_shops,
            "greedy_distance_meters": tsp_result["greedy_dist_meters"],
            "optimized_distance_meters": tsp_result["opt_dist_meters"],
            "optimized_order_ids": ordered_shop_ids
        }
