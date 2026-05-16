from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class PlaceResponse(BaseModel):
    id: int
    place_id: Optional[str] = None
    name: str 
    category: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lon: float
    distance_meters: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    image_url: Optional[str] = None
    match_score: Optional[float] = None
    class Config:
        from_attributes = True

class NearbySearchResponse(BaseModel):
    user_location: dict
    search_radius_meters: int
    total_found: int
    places: List[PlaceResponse]

class StoreResponse(BaseModel):
    store_id: Optional[int] = None
    place_id: Optional[str] = None
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lon: float
    phone: Optional[str] = None
    rating: Optional[float] = None
    class Config:
        from_attributes = True

class NearbyStoreItem(StoreResponse):
    distance_m: Optional[float] = None

class NearbyStoreResponse(BaseModel):
    user_location: dict
    search_radius_meters: int
    total_found: int
    stores: List[NearbyStoreItem]

class ClusterItem(BaseModel):
    cluster_id: int
    center: dict
    places: List[PlaceResponse]
    stores: List[StoreResponse]

class ClusterRequest(BaseModel):
    place_ids: List[int]

class ClusterResponse(BaseModel):
    clusters: List[ClusterItem]

class RoutePlanRequest(BaseModel):
    current_lat: float = Field(..., ge=-90, le=90)
    current_lon: float = Field(..., ge=-180, le=180)
    place_ids: List[int]

class RoutePlanResponse(BaseModel):
    total_distance_meters: float
    waypoints: List[dict]
    polyline: Optional[Union[str, dict]] = None
    optimized_order: List[int]
    weather_context: Optional[dict] = None

class ProductCompactResponse(BaseModel):
    product_id: int
    name: str
    price: float
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

class StoreWithProductsResponse(StoreResponse):
    products: List[ProductCompactResponse]

class O2OContextResponse(BaseModel):
    place_info: PlaceResponse
    nearby_stores: List[StoreWithProductsResponse]