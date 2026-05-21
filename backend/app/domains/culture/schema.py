from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceDetailWithAI(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    place_id: str
    name: str
    category: str | None = None
    address: str | None = None
    lat: float
    lon: float
    ai_story: str | None = None


class ReviewCreate(BaseModel):
    author_name: str | None = Field(default=None, max_length=100)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=1000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, min_length=3, max_length=1000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    place_id: str
    author_name: str
    rating: int
    text: str
    time_posted: str
    user_id: UUID | None = None
    moderation_status: str = "visible"
    report_count: int = 0


class ReviewActionResponse(BaseModel):
    id: int
    status: str


class PlaceImageResponse(BaseModel):
    image_url: str | None = None
