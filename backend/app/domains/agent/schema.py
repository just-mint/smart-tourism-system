from pydantic import BaseModel
from typing import Optional, List

class AgentChatRequest(BaseModel):
    query: str
    lat: Optional[float] = None
    lon: Optional[float] = None

class AgentChatResponse(BaseModel):
    answer: str
    internal_actions: List[str]
