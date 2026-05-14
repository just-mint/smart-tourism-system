from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser, SessionDep
from sqlalchemy import func, select
from app.models import User
from app.domains.culture.model import Place
from app.domains.inventory.model import Store, InventoryLock
from app.models import Message
from app.utils import generate_test_email, send_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True

@router.get("/telemetry/")
def get_telemetry(session: SessionDep) -> dict:
    active_users = session.scalar(select(func.count()).select_from(User))
    total_places = session.scalar(select(func.count()).select_from(Place))
    total_stores = session.scalar(select(func.count()).select_from(Store))
    active_locks = session.scalar(select(func.count()).select_from(InventoryLock))
    
    return {
        "active_users": active_users or 0,
        "total_places": total_places or 0,
        "total_stores": total_stores or 0,
        "active_locks": active_locks or 0,
    }
