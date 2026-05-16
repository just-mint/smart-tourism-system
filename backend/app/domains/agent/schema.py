
from pydantic import BaseModel


class AgentChatRequest(BaseModel):
    query: str
    current_lat: float | None = None
    current_lon: float | None = None

class AgentChatResponse(BaseModel):
    answer: str
    internal_actions: list[str]
