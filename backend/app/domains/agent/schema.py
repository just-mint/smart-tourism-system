from pydantic import BaseModel
from typing import Optional, List

class AgentChatRequest(BaseModel):
    query: str
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None

class AgentChatResponse(BaseModel):
    answer: str
    internal_actions: List[str]
