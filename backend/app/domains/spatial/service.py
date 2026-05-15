from sqlalchemy.orm import Session
from sqlalchemy import func, text
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_Distance
from app.domains.culture.model import Place
from app.domains.inventory.model import Store
import os
import httpx
import math
import numpy as np
from sklearn.cluster import KMeans

from sqlalchemy import cast
from geoalchemy2.types import Geography

def search_places_omnisearch(db: Session, query_text: str, user_lat: float = None, user_lon: float = None):
    if not query_text or len(query_text) < 2:
        return []
    
    # --- COMPOSITE RANKING ALGORITHM ---
    # Trọng số: 40% Độ khớp tên | 40% Khoảng cách gần | 20% Đánh giá
    W_SIMILARITY = 0.4
    W_DISTANCE = 0.4
    W_RATING = 0.2
    MAX_RADIUS = 50000  # 50km — không đề xuất xa hơn
    
    similarity_col = func.similarity(Place.name, query_text).label('sim_score')
    
    if user_lat is not None and user_lon is not None:
        # Có tọa độ người dùng → tính khoảng cách bằng PostGIS
        user_location = cast(
            WKTElement(f'POINT({user_lon} {user_lat})', srid=4326),
            Geography(srid=4326)
        )
        distance_col = ST_Distance(
            Place.geom.cast(Geography(srid=4326)), user_location
        ).label('distance_m')
        
        query = db.query(Place, similarity_col, distance_col) \
                  .filter(Place.name.ilike(f'%{query_text}%')) \
                  .filter(ST_DWithin(Place.geom.cast(Geography(srid=4326)), user_location, MAX_RADIUS)) \
                  .order_by(similarity_col.desc()) \
                  .limit(20)
        rows = query.all()
    else:
        # Không có tọa độ → chỉ dùng similarity
        query = db.query(Place, similarity_col) \
                  .filter(Place.name.ilike(f'%{query_text}%')) \
                  .order_by(similarity_col.desc()) \
                  .limit(10)
        rows = [(p, sim, None) for p, sim in query.all()]
    
    if not rows:
        return []
    
    # Tính final_score cho từng kết quả
    scored = []
    for row in rows:
        p, sim_score, dist = row[0], float(row[1] or 0), row[2]
        
        # 1. Similarity score (0-1)
        s_sim = sim_score
        
        # 2. Distance score (0-1): Gần = điểm cao, xa = điểm thấp
        if dist is not None:
            dist_m = float(dist)
            s_dist = max(0, 1.0 - (dist_m / MAX_RADIUS))
        else:
            s_dist = 0.5  # Không có GPS → neutral
        
        # 3. Rating score (0-1): Chuẩn hóa rating/5.0
        raw_rating = float(p.rating) if p.rating else 0.0
        s_rating = min(raw_rating / 5.0, 1.0)
        
        # Composite score (0-100)
        final = (W_SIMILARITY * s_sim + W_DISTANCE * s_dist + W_RATING * s_rating) * 100
        
        scored.append({
            "id": p.id,
            "place_id": str(p.place_id) if p.place_id else None,
            "name": p.name,
            "category": p.category,
            "address": p.address,
            "lat": float(p.lat) if p.lat else None,
            "lon": float(p.lon) if p.lon else None,
            "distance_meters": round(float(dist), 1) if dist is not None else None,
            "rating": float(p.rating) if p.rating else None,
            "match_score": round(final, 1)
        })
    
    # Sắp xếp NGHIÊM NGẶT từ cao xuống thấp
    scored.sort(key=lambda x: x['match_score'], reverse=True)
    return scored[:10]

def get_nearby_places(db: Session, lat: float, lon: float, radius_meters: int = 2000):
    user_location = cast(WKTElement(f'POINT({lon} {lat})', srid=4326), Geography(srid=4326))
    query = db.query(Place, ST_Distance(Place.geom.cast(Geography(srid=4326)), user_location).label('distance')) \
            .filter(ST_DWithin(Place.geom.cast(Geography(srid=4326)), user_location, radius_meters)) \
            .order_by(ST_Distance(Place.geom.cast(Geography(srid=4326)), user_location))
    results = query.all()
    return [
        {
            "id": p.id, 
            "place_id": str(p.place_id) if p.place_id else None, 
            "name": p.name, 
            "category": p.category, 
            "address": p.address, 
            "lat": float(p.lat) if p.lat else None, 
            "lon": float(p.lon) if p.lon else None, 
            "distance_meters": round(float(d), 2) if d else None
        } 
        for p, d in results
    ]

def cluster_stores_around_places(db: Session, place_ids: list[int]):
    places = db.query(Place).filter(Place.id.in_(place_ids)).all()
    if not places:
        return {"clusters": []}

    # 1. Tính Bounding Box của các Place được chọn
    lats = [float(p.lat) for p in places if p.lat is not None]
    lons = [float(p.lon) for p in places if p.lon is not None]
    if not lats:
        return {"clusters": []}

    # Mở rộng bounding box thêm ~1km (xấp xỉ 0.01 độ)
    lat_min, lat_max = min(lats) - 0.01, max(lats) + 0.01
    lon_min, lon_max = min(lons) - 0.01, max(lons) + 0.01

    # 2. Query stores trong bounding box (cực nhanh nhờ GIST index)
    # Dùng raw SQL để chắc chắn đúng cú pháp PostGIS
    store_rows = db.execute(text("""
        SELECT store_id, name, lat::float, lon::float, category, address
        FROM stores
        WHERE geom IS NOT NULL
          AND lat BETWEEN :lat_min AND :lat_max
          AND lon BETWEEN :lon_min AND :lon_max
        
    """), {"lat_min": lat_min, "lat_max": lat_max,
           "lon_min": lon_min, "lon_max": lon_max}).fetchall()

    # 3. Gom dữ liệu cho KMeans
    points = []
    metadata = []
    for p in places:
        if p.lat and p.lon:
            points.append([float(p.lat), float(p.lon)])
            metadata.append(("place", {
                "id": p.id,
                "place_id": str(p.place_id) if p.place_id else None,
                "name": p.name,
                "category": p.category,
                "address": p.address,
                "lat": float(p.lat),
                "lon": float(p.lon)
            }))

    for s in store_rows:
        if s[2] and s[3]:
            points.append([s[2], s[3]])
            metadata.append(("store", {
                "store_id": s[0],
                "place_id": None,
                "name": s[1],
                "category": s[4],
                "address": s[5],
                "lat": s[2],
                "lon": s[3]
            }))

    if len(points) < 2:
        return {"clusters": [{"cluster_id": 1, "center": {"lat": lats[0], "lon": lons[0]}, "places": [m[1] for m in metadata if m[0]=="place"], "stores": [m[1] for m in metadata if m[0]=="store"]}]}

    # 4. KMeans — giới hạn 2-5 cụm tự động
    n_clusters = min(max(2, len(places)), 5, len(points))
    X = np.array(points)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(X)
    centers = kmeans.cluster_centers_

    clusters = []
    for i in range(n_clusters):
        c_places, c_stores = [], []
        for idx, label in enumerate(labels):
            if label == i:
                typ, obj = metadata[idx]
                if typ == "place":
                    c_places.append(obj)
                else:
                    c_stores.append(obj)
        clusters.append({
            "cluster_id": i + 1,
            "center": {"lat": round(centers[i][0], 6), "lon": round(centers[i][1], 6)},
            "places": c_places,
            "stores": c_stores
        })

    return {"clusters": clusters}



async def fetch_real_weather(lat: float, lon: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                cw = res.json().get("current_weather", {})
                temp = cw.get("temperature")
                code = cw.get("weathercode")
                # Chuẩn hóa WMO Weather Code
                condition = "Clear"
                if code in [61, 63, 65, 80, 81, 82]: condition = "Rainy"
                elif code in [95, 96, 99]: condition = "Storm"
                elif code in [1, 2, 3]: condition = "Cloudy"
                
                return {"temperature": temp, "condition": condition, "code": code}
    except Exception:
        pass
    return {"temperature": 30, "condition": "Unknown", "code": -1}

async def plan_route_osrm(db: Session, current_lat: float, current_lon: float, place_ids: list[int]):
    places = db.query(Place).filter(Place.id.in_(place_ids)).all()
    if not places: raise ValueError("Không tìm thấy địa điểm nào khớp với place_ids cung cấp")

    weather = await fetch_real_weather(current_lat, current_lon)
    place_dicts = [{"id": p.id, "lat": float(p.lat), "lon": float(p.lon), "name": p.name} for p in places if p.lat and p.lon]

    if not place_dicts:
        raise ValueError("Các địa điểm được chọn không có tọa độ hợp lệ")

    coords = [f"{current_lon},{current_lat}"]
    for p in place_dicts: coords.append(f"{p['lon']},{p['lat']}")
    
    coords_str = ";".join(coords)
    # 1. Use OSRM Trip API to calculate actual road distance TSP
    osrm_base = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
    url = f"{osrm_base}/trip/v1/driving/{coords_str}?source=first&roundtrip=false&overview=full&geometries=geojson"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise ValueError(f"OSRM Server Error: {response.status_code}")
            data = response.json()

        if data.get("code") != "Ok":
            raise ValueError(f"OSRM No Route: {data.get('code')}")

        trip = data['trips'][0]
        
        # 2. Extract TSP order from waypoints array (skipping source at index 0)
        ordered_places = []
        for i, wp in enumerate(data['waypoints'][1:]):
            ordered_places.append((wp['waypoint_index'], place_dicts[i]))
            
        ordered_places.sort(key=lambda x: x[0])
        optimized_order_ids = [p['id'] for _, p in ordered_places]
        
        osrm_waypoints = [{"lat": p['lat'], "lon": p['lon'], "name": p['name']} for _, p in ordered_places]

        return {
            "total_distance_meters": trip['distance'],
            "waypoints": osrm_waypoints,
            "polyline": trip['geometry'],
            "optimized_order": optimized_order_ids,
            "weather_context": weather
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[Route] OSRM Trip fallback: {e}")
        # Fallback
        return {
            "total_distance_meters": 0.0,
            "waypoints": [{"lat": p["lat"], "lon": p["lon"], "name": p["name"]} for p in place_dicts],
            "polyline": None,
            "optimized_order": [p['id'] for p in place_dicts],
            "weather_context": weather
        }

def get_place_o2o_context(db: Session, place_id: str, radius: int = 2000):
    from sqlalchemy import func
    from app.domains.inventory.model import Store, Inventory, Product
    
    place = db.query(Place).filter(Place.place_id == place_id).first()
    if not place:
        raise ValueError("Không tìm thấy địa điểm")
        
    place_info = {
        "id": place.id,
        "place_id": place.place_id,
        "name": place.name,
        "category": place.category,
        "address": place.address,
        "lat": float(place.lat) if place.lat else 0.0,
        "lon": float(place.lon) if place.lon else 0.0
    }
    
    nearby_stores = []
    if place.lat and place.lon:
        point = f"SRID=4326;POINT({place.lon} {place.lat})"
        # Tìm stores trong bán kính radius
        stores = db.query(Store).filter(
            Store.category == 'shopping',
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius)
        ).all()
        
        if stores:
            store_ids = [s.store_id for s in stores]
            # Query tất cả inventory và product của các store này trong 1 câu lệnh (Tránh N+1)
            results = db.query(Inventory, Product).join(
                Product, Inventory.product_id == Product.product_id
            ).filter(
                Inventory.store_id.in_(store_ids)
            ).all()
            
            from collections import defaultdict
            store_products = defaultdict(list)
            for inv, prod in results:
                store_products[inv.store_id].append({
                    "product_id": prod.product_id,
                    "name": prod.name,
                    "price": prod.price,
                    "image_url": prod.image_url
                })
            
            for s in stores:
                nearby_stores.append({
                    "store_id": s.store_id,
                    "place_id": s.place_id,
                    "name": s.name,
                    "category": s.category,
                    "address": s.address,
                    "lat": float(s.lat) if s.lat else 0.0,
                    "lon": float(s.lon) if s.lon else 0.0,
                    "products": store_products.get(s.store_id, [])
                })
            
    return {
        "place_info": place_info,
        "nearby_stores": nearby_stores
    }