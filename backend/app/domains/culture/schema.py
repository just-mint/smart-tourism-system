import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field

class PlaceDetailWithAI(BaseModel):
    id: int
    place_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    lat: float
    lon: float
    ai_story: Optional[str] = None
    story_source: str = "fallback"
    story_cached: bool = False
    content_sources: list[str] = Field(default_factory=list)
    opening_hours: Optional[str] = None
    ticket_price: Optional[str] = None
    rules: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    image_source: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=1000)

class ReviewModerationUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    moderation_note: Optional[str] = Field(default=None, max_length=500)

class ReviewReportCreate(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)

class ReviewResponse(BaseModel):
    id: int
    place_id: str
    user_id: Optional[uuid.UUID] = None
    author_name: str
    rating: int
    text: str
    time_posted: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    report_count: int = 0
    moderation_note: Optional[str] = None
    class Config:
        from_attributes = True

class CultureMetadataResponse(BaseModel):
    total_places: int
    total_categories: int
    total_stores: int
    approved_reviews: int

class WikiImageResponse(BaseModel):
    image_url: Optional[str] = None
    source: str = "fallback"
