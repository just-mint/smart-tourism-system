
from pydantic import BaseModel


class PlaceDetailWithAI(BaseModel):
    id: int
    place_id: str
    name: str
    category: str | None = None
    address: str | None = None
    lat: float
    lon: float
    ai_story: str | None = None

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
