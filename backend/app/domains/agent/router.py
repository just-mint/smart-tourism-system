from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.agent import schema, service

router = APIRouter()

@router.post("/chat", response_model=schema.AgentChatResponse)
async def chat_with_agent_endpoint(request: schema.AgentChatRequest, db: Session = Depends(get_db)):
    """
    Agent Gateway: Chứa NÃO THẬT. Gọi chéo API ngầm.
    """
    return await service.chat_with_agent(db, request)
