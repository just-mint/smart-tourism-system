
from pydantic import BaseModel, Field


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
    author_name: str | None = Field(default=None, max_length=100)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=1000)

class ReviewResponse(BaseModel):
    id: int
    place_id: str
    author_name: str
    rating: int
    text: str
    time_posted: str
    class Config:
        from_attributes = True


class PlaceImageResponse(BaseModel):
    image_url: str | None = None
