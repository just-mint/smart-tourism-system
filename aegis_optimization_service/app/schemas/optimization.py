from pydantic import BaseModel, Field
from typing import List

class Coords(BaseModel):
    lat: float
    lng: float

class ShopItem(BaseModel):
    id: str
    name: str
    address: str
    coords: Coords
    category: str
    price: int
    rating: float
    description_raw: str

class OptimizationRequest(BaseModel):
    user_lat: float
    user_lon: float
    shops: List[ShopItem]
    top_n: int = Field(default=3, ge=1)
    w_rating: float = 0.4
    w_distance: float = 0.3
    w_price: float = 0.3

class OptimizationResponse(BaseModel):
    total_input_shops: int
    selected_shops: List[dict]
    greedy_distance_meters: float
    optimized_distance_meters: float
    optimized_order_ids: List[str]
