import httpx
import math

class TSPSolver:
    OSRM_BASE_URL = "http://router.project-osrm.org"

    @classmethod
    async def fetch_distance_matrix(cls, coords: list[tuple[float, float]]):
        """ 
        Bước 1: Gọi API OSRM (Table service) để lấy Ma trận khoảng cách 
        - coords truyền vào dạng danh sách tuple (lon, lat)
        """
        coord_strings = [f"{lon},{lat}" for lon, lat in coords]
        coords_joined = ";".join(coord_strings)
        url = f"{cls.OSRM_BASE_URL}/table/v1/driving/{coords_joined}?annotations=distance"
        
        try:
            # Ngưỡng Timeout: 5.0 giây theo kiến nghị thay vì 3.0 giây để chờ tính ma trận ổn định
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == "Ok":
                        return data.get("distances")
        except Exception as e:
            print(f"[!] Lỗi gọi OSRM Table API: {e}")
            pass
        
        # Fallback khẩn trương (Haversine Matrix) khi OSRM bảo trì / lỗi mạng
        print("[!] Không lấy được Matrix từ OSRM. Hệ thống chuyển sang Fallback Local Haversine.")
        return cls._fallback_distance_matrix(coords)
        
    @staticmethod
    def _fallback_distance_matrix(coords: list[tuple[float, float]]):
        """ Dự phòng OSRM Failed: Tính khoảng cách đường chim bay giữa mọi cặp toạ độ (mét) """
        def haversine(lon1, lat1, lon2, lat2):
            R = 6371000 # Bán kính Trái Đất (mét)
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(delta_lambda/2.0)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
        N = len(coords)
        matrix = [[0.0 for _ in range(N)] for _ in range(N)]
        for i in range(N):
            for j in range(N):
                matrix[i][j] = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
        return matrix

    @staticmethod
    def calculate_tour_distance(tour: list[int], distance_matrix: list[list[float]]):
        """ Tính tổng quãng đường của một lộ trình dựa trên ma trận có sẵn """
        return sum(distance_matrix[tour[i]][tour[i+1]] for i in range(len(tour)-1))

    @staticmethod
    def reorder_shops(original_shops: list[dict], path_indexes: list[int]) -> list[dict]:
        """ Sắp xếp lại danh sách shop thực tế theo mảng Index từ thuật toán TSP """
        ordered_shops = []
        for idx in path_indexes:
            if idx == 0:
                continue # Bỏ qua index 0 vì đó là điểm xuất phát (User)
            ordered_shops.append(original_shops[idx - 1])
        return ordered_shops

    @classmethod
    def nearest_neighbor(cls, distance_matrix: list[list[float]]):
        """ Bước 2: Khởi tạo lộ trình ban đầu bằng Local Search (Greedy/Nearest Neighbor) """
        N = len(distance_matrix)
        unvisited = set(range(1, N))
        tour = [0] # 0 = Origin (Người dùng đang đứng)
        current = 0
        while unvisited:
            # Chọn địa điểm có khoảng cách ngắn nhất tính từ current (Tránh None hoặc Infinity)
            next_node = min(unvisited, key=lambda node: distance_matrix[current][node] if distance_matrix[current][node] is not None else float('inf'))
            unvisited.remove(next_node)
            tour.append(next_node)
            current = next_node
        return tour

    @classmethod
    def optimize_2opt(cls, tour: list[int], distance_matrix: list[list[float]]):
        """ Bước 3: Áp dụng thuật toán tối ưu cục bộ 2-Opt (2-Optimization) """
        best_tour = tour[:]
        best_distance = cls.calculate_tour_distance(best_tour, distance_matrix)
        improved = True
        
        while improved:
            improved = False
            # Bắt đầu đảo mắt xích nhưng tránh Node đầu tiên bị thay đổi (Vị trí user là mỏ neo cố định)
            for i in range(1, len(best_tour) - 1):
                for j in range(i + 1, len(best_tour) + 1):
                    # Khởi tạo lộ trình hoán vị qua slice [::-1] 
                    new_tour = best_tour[:i] + best_tour[i:j][::-1] + best_tour[j:]
                    
                    new_distance = cls.calculate_tour_distance(new_tour, distance_matrix)
                    if new_distance < best_distance:
                        best_distance = new_distance
                        best_tour = new_tour
                        improved = True
                        break # Phá lặp trong tìm kiếm tổ hợp để bắt đầu lại vòng lặp 2-Opt
                if improved:
                    break
        return best_tour, best_distance

    @classmethod
    async def run_tsp_pipeline(cls, user_coord: tuple[float, float], shop_coords: list[tuple[float, float]]):
        """ Đường ống (Pipeline) chạy thuật toán hoàn chỉnh """
        # Định nghĩa Index 0: User | Index > 0: Shops
        coords = [user_coord] + shop_coords
        
        # 1. Fetch OSRM Matrix (N x N)
        matrix = await cls.fetch_distance_matrix(coords)
        
        # 2. Sinh Baseline Lộ trình (Greedy)
        greedy_tour = cls.nearest_neighbor(matrix)
        greedy_dist = cls.calculate_tour_distance(greedy_tour, matrix)
        
        # 3. Tối ưu cực hạn bằng 2-Opt Algorithm
        opt_tour, opt_dist = cls.optimize_2opt(greedy_tour, matrix)
        
        return {
            "greedy_dist_meters": round(greedy_dist, 2),
            "opt_dist_meters": round(opt_dist, 2),
            "greedy_path_indexes": greedy_tour,
            "opt_path_indexes": opt_tour,
            "distance_matrix": matrix
        }
