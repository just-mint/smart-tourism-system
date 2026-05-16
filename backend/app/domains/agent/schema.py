
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    current_lat: float | None = Field(default=None, ge=-90, le=90)
    current_lon: float | None = Field(default=None, ge=-180, le=180)

class AgentChatResponse(BaseModel):
    answer: str
    internal_actions: list[str]
