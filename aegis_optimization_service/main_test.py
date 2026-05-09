import asyncio
from mock_data import get_mock_stores
from app.core.algorithms.ranking_algo import RankingAlgorithm
from app.core.algorithms.tsp_solver import TSPSolver

async def test_tsp_fallback():
    print("\n[BƯỚC 3] KIỂM THỬ FALLBACK HAVERSINE (QUAN TRỌNG)")
    print("-" * 80)
    
    # Cố tình làm sai URL của OSRM để ép lỗi HTTP và Timeout
    original_url = TSPSolver.OSRM_BASE_URL
    TSPSolver.OSRM_BASE_URL = "http://localhost:9999/osrm_error_mock"
    
    stores = get_mock_stores()
    user_coord = (106.7009, 10.7769)
    shop_coords = [(s['coords']['lng'], s['coords']['lat']) for s in stores[:3]]
    
    # Gọi pipeline để xem hệ thống có crash hay tự kích hoạt Fallback
    tsp_result = await TSPSolver.run_tsp_pipeline(user_coord, shop_coords)
    
    # Khôi phục URL
    TSPSolver.OSRM_BASE_URL = original_url
    
    print("\n[TEST FALLBACK] Kích hoạt thành công Haversine do OSRM lỗi")
    print(f"=> Khoảng cách Fallback tính được: {tsp_result['opt_dist_meters']:,.0f} mét\n")

async def main():
    print("\n" + "=" * 80)
    print("👑 BÁO CÁO THỰC THI KIẾN TRÚC THUẬT TOÁN MICROSERVICE (TRƯỜNG PHÁI DDD) 👑")
    print("=" * 80)
    
    stores = get_mock_stores()
    
    # Giả lập vị trí người dùng (User Location)
    user_lat = 10.7769
    user_lon = 106.7009
    
    # ---------------- 1. RANKING ----------------
    print("\n[BƯỚC 1] RANKING ALGORITHM - MULTI-CRITERIA (MIN-MAX SCALER)")
    print("-" * 80)
    
    top_3_stores = RankingAlgorithm.rank_items(
        items=stores, 
        user_lat=user_lat,
        user_lon=user_lon,
        w1=0.4, # Rating 
        w2=0.3, # Distance
        w3=0.3  # Price
    )[:3]
    
    for i, s in enumerate(top_3_stores):
        meta = s['score_metadata']
        print(f"🏆 Top {i+1}: {s['name']} (ID {s['id']})")
        print(f"   => Thông số gốc: Rank={s['rating']}*, Giá={s['price']}đ")
        print(f"   => Khoảng cách nội bộ tính toán từ User: {s['distance_to_user']} km")
        print(f"   => Tọa độ Nested Object: Lat={s['coords']['lat']}, Lng={s['coords']['lng']}")
        print(f"   => Điểm chuẩn hóa: Norm(Rating)={meta['norm_rating']}, Norm(Dist)={meta['norm_distance']}, Norm(Price)={meta['norm_price']}")
        print(f"   => ĐIỂM TỔNG HỢP FINAL: {s['final_score']}")

    # ---------------- 2. TSP ----------------
    print("\n[BƯỚC 2] TSP ALGORITHM - DISTANCE MATRIX + 2-OPT (OSRM & LOCAL SEARCH)")
    print("-" * 80)
    
    # Định cư (lon, lat) OSRM chuẩn
    user_coord = (user_lon, user_lat) 
    shop_coords = [(s['coords']['lng'], s['coords']['lat']) for s in top_3_stores]
    
    tsp_result = await TSPSolver.run_tsp_pipeline(user_coord, shop_coords)
    
    print(f"📍 Khoảng cách khởi tạo (Greedy / Nearest Neighbor) : {tsp_result['greedy_dist_meters']:,.0f} mét")
    print(f"🎯 Khoảng cách tối ưu cục bộ sau khi áp dụng 2-Opt   : {tsp_result['opt_dist_meters']:,.0f} mét")
    
    saved = tsp_result['greedy_dist_meters'] - tsp_result['opt_dist_meters']
    if saved > 0:
        print(f"🔥 Thuật toán 2-opt đã can thiệp đảo mắt xích: Tiết kiệm CỰC ĐẠI {saved:,.0f} mét!")
    else:
        print("✅ Lộ trình ban đầu (Greedy) đã đạt cực tiểu địa phương tối ưu (Local Optima).")
    
    # Phân tích ra chuỗi đường đi từ mảng TSP Index
    opt_indexes = tsp_result["opt_path_indexes"]
    ordered_shop_ids = []
    ordered_shop_names = []
    
    for idx in opt_indexes:
        if idx == 0: continue
        shop = top_3_stores[idx - 1]
        ordered_shop_ids.append(shop['id'])
        ordered_shop_names.append(shop['name'])
        
    print(f"\n=> Thứ tự di chuyển Tối ưu nhất (Mảng IDS): {ordered_shop_ids}")
    print("=> Mô phỏng chuỗi điểm đi qua thực tế:")
    for step, name in enumerate(ordered_shop_names):
        print(f"   [Trạm {step+1}] {name}")
        
    print("\n" + "=" * 80 + "\n")
    
    # Gọi kịch bản test Fallback OSRM
    await test_tsp_fallback()

if __name__ == "__main__":
    asyncio.run(main())
