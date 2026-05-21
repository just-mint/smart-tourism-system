from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.domains.agent import schema, service
from app.models import User

router = APIRouter()


@router.post(
    "/chat",
    response_model=schema.AgentChatResponse,
    dependencies=[Depends(rate_limit(limit=20, window_seconds=60))],
)
async def chat_with_agent_endpoint(
    request: schema.AgentChatRequest,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Agent Gateway: Chứa NÃO THẬT. Gọi chéo API ngầm.
    """
    return await service.chat_with_agent(db, request)
