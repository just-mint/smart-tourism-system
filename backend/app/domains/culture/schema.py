from pydantic import BaseModel
from typing import Optional

class PlaceDetailWithAI(BaseModel):
    id: int
    place_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lon: float
    ai_story: Optional[str] = None

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    author_name: str
    rating: int
    text: str

class ReviewResponse(BaseModel):
    id: int
    place_id: str
    author_name: str
    rating: int
    text: str
    time_posted: str
    class Config:
        from_attributes = True
