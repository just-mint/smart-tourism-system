import math

class RankingAlgorithm:
    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """ Tính toán khoảng cách trắc địa bằng công thức Haversine (đơn vị: km) """
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

    @staticmethod
    def normalize_min_max(value: float, min_val: float, max_val: float, inverse: bool = False) -> float:
        """ Chuẩn hóa Min-Max Scaler về dải [0, 1] """
        if max_val == min_val: return 1.0  
        if not inverse:
            return (value - min_val) / (max_val - min_val)
        else:
            return (max_val - value) / (max_val - min_val)

    @classmethod
    def rank_items(cls, items: list[dict], user_lat: float, user_lon: float, w1: float = 0.4, w2: float = 0.3, w3: float = 0.3) -> list[dict]:
        """ Đánh giá điểm theo Multi-criteria Decision """
        if not items: return []
            
        ratings = []
        distances = []
        prices = []
        
        # Tiền xử lý để bóc tách toạ độ lồng (coords.lat, coords.lng) cho tính toán khoảng cách
        for item in items:
            lat = item['coords']['lat']
            lng = item['coords']['lng']
            dist = cls.haversine_distance_km(user_lat, user_lon, lat, lng)
            
            # Lưu trữ linh hoạt thông số distance_to_user vào dict nội bộ để xử lý Min-Max
            item['distance_to_user'] = round(dist, 4)
            
            ratings.append(item['rating'])
            distances.append(dist)
            prices.append(item['price'])
        
        min_r, max_r = min(ratings), max(ratings)
        min_d, max_d = min(distances), max(distances)
        min_p, max_p = min(prices), max(prices)
        
        for item in items:
            r = item['rating']
            d = item['distance_to_user']
            p = item['price']
            
            norm_r = cls.normalize_min_max(r, min_r, max_r, inverse=False)
            norm_d = cls.normalize_min_max(d, min_d, max_d, inverse=True)
            norm_p = cls.normalize_min_max(p, min_p, max_p, inverse=True)
            
            final_score = (w1 * norm_r) + (w2 * norm_d) + (w3 * norm_p)
            
            item['score_metadata'] = {
                'norm_rating': round(norm_r, 4),
                'norm_distance': round(norm_d, 4),
                'norm_price': round(norm_p, 4)
            }
            item['final_score'] = round(final_score, 4)
            
        return sorted(items, key=lambda x: x['final_score'], reverse=True)

    @classmethod
    def calculate_total_metrics(cls, ordered_shops: list[dict], distance_matrix: list[list[float]]) -> dict:
        """ Tính tổng chi phí và tổng quãng đường của lộ trình đã sắp xếp """
        total_price = sum(int(shop.get('price', 0)) for shop in ordered_shops)
        
        total_distance_km = 0.0
        # Ước tính khoảng cách thực tế giữa các shop trong lộ trình thông qua Haversine
        for i in range(len(ordered_shops) - 1):
            lat1, lon1 = ordered_shops[i]['coords']['lat'], ordered_shops[i]['coords']['lng']
            lat2, lon2 = ordered_shops[i+1]['coords']['lat'], ordered_shops[i+1]['coords']['lng']
            total_distance_km += cls.haversine_distance_km(lat1, lon1, lat2, lon2)
            
        return {
            "total_price": total_price,
            "total_distance_km": round(total_distance_km, 2)
        }
