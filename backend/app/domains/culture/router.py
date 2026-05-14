from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.domains.culture import service, schema
from app.domains.spatial.schema import PlaceResponse
from app.api.deps import get_current_active_superuser, get_current_user
from app.models import User

router = APIRouter()

@router.get("/metadata", response_model=schema.CultureMetadataResponse)
def get_culture_metadata(db: Session = Depends(get_db)):
    return service.get_culture_metadata(db=db)

@router.get("/wiki-image", response_model=schema.WikiImageResponse)
async def get_wiki_image(title: str, category: str | None = None):
    return await service.get_wikipedia_image(title=title, category=category)

@router.get("/places/search", response_model=List[PlaceResponse])
def search_culture_places(q: str, db: Session = Depends(get_db)):
    """Tìm kiếm nhanh địa danh theo từ khóa (Tìm Text trong 1.7M Dataset)"""
    return service.search_places_by_name(db=db, keyword=q)

@router.get("/places/{id}/story", response_model=schema.PlaceDetailWithAI)
async def get_ai_story(id: int, db: Session = Depends(get_db)):
    result = await service.generate_place_story(db=db, place_id=id)
    if not result:
         raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return result

@router.post("/places/{id}/reviews", response_model=schema.ReviewResponse)
def add_review(
    id: int,
    review: schema.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = service.create_place_review(
        db=db, place_id=id, review_data=review, user=current_user
    )
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return result

@router.get("/places/{id}/reviews", response_model=List[schema.ReviewResponse])
def get_reviews(id: int, db: Session = Depends(get_db)):
    return service.get_place_reviews(db=db, place_id=id)

@router.post("/reviews/{review_id}/report", response_model=schema.ReviewResponse)
def report_review(
    review_id: int,
    report: schema.ReviewReportCreate,
    db: Session = Depends(get_db),
):
    result = service.report_review(db=db, review_id=review_id, data=report)
    if not result:
        raise HTTPException(status_code=404, detail="KhĂ´ng tĂ¬m tháº¥y Ä‘Ă¡nh giĂ¡")
    return result

@router.get(
    "/reviews/moderation",
    response_model=List[schema.ReviewResponse],
    dependencies=[Depends(get_current_active_superuser)],
)
def list_reviews_for_moderation(status: str = "pending", db: Session = Depends(get_db)):
    if status not in {"pending", "approved", "rejected", "all"}:
        raise HTTPException(status_code=400, detail="Invalid review status")
    return service.list_reviews_for_moderation(db=db, status=status)

@router.patch("/reviews/{review_id}/moderation", response_model=schema.ReviewResponse)
def moderate_review(
    review_id: int,
    data: schema.ReviewModerationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    result = service.moderate_review(
        db=db, review_id=review_id, data=data, moderator=current_user
    )
    if not result:
        raise HTTPException(status_code=404, detail="KhĂ´ng tĂ¬m tháº¥y Ä‘Ă¡nh giĂ¡")
    return result
