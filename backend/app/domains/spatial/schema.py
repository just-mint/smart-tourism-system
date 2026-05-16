
from pydantic import BaseModel, Field


class PlaceResponse(BaseModel):
    id: int
    place_id: str | None = None
    name: str
    category: str | None = None
    address: str | None = None
    lat: float
    lon: float
    distance_meters: float | None = None
    phone: str | None = None
    rating: float | None = None
    review_count: int | None = None
    image_url: str | None = None
    match_score: float | None = None
    class Config:
        from_attributes = True

class NearbySearchResponse(BaseModel):
    user_location: dict
    search_radius_meters: int
    total_found: int
    places: list[PlaceResponse]

class StoreResponse(BaseModel):
    store_id: int | None = None
    place_id: str | None = None
    name: str
    category: str | None = None
    address: str | None = None
    lat: float
    lon: float
    phone: str | None = None
    rating: float | None = None
    class Config:
        from_attributes = True

class NearbyStoreItem(StoreResponse):
    distance_m: float | None = None

class NearbyStoreResponse(BaseModel):
    user_location: dict
    search_radius_meters: int
    total_found: int
    stores: list[NearbyStoreItem]

class ClusterItem(BaseModel):
    cluster_id: int
    center: dict
    places: list[PlaceResponse]
    stores: list[StoreResponse]

class ClusterRequest(BaseModel):
    place_ids: list[int]

class ClusterResponse(BaseModel):
    clusters: list[ClusterItem]

class RoutePlanRequest(BaseModel):
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    place_ids: list[int]

class RoutePlanResponse(BaseModel):
    total_distance_meters: float
    waypoints: list[dict]
    polyline: str | dict | None = None
    optimized_order: list[int]
    weather_context: dict | None = None
    routing_fallback_used: bool = False

class ProductCompactResponse(BaseModel):
    product_id: int
    name: str
    price: float
    image_url: str | None = None
    class Config:
        from_attributes = True

class StoreWithProductsResponse(StoreResponse):
    products: list[ProductCompactResponse]

class O2OContextResponse(BaseModel):
    place_info: PlaceResponse
    nearby_stores: list[StoreWithProductsResponse]
