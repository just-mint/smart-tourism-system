
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.domains.culture import schema, service
from app.domains.spatial.schema import PlaceResponse
from app.models import User

router = APIRouter()

@router.get("/places/search", response_model=list[PlaceResponse])
def search_culture_places(q: str, db: Session = Depends(get_db)):
    """Tìm kiếm nhanh địa danh theo từ khóa (Tìm Text trong 1.7M Dataset)"""
    return service.search_places_by_name(db=db, keyword=q)

@router.get("/places/{id}/story", response_model=schema.PlaceDetailWithAI)
async def get_ai_story(id: int, db: Session = Depends(get_db)):
    result = await service.generate_place_story(db=db, place_id=id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return result


@router.get("/stores/{store_id}/story", response_model=schema.PlaceDetailWithAI)
async def get_store_ai_story(store_id: int, db: Session = Depends(get_db)):
    result = await service.generate_store_place_story(db=db, store_id=store_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm gắn với cửa hàng")
    return result


@router.get("/places/{id}/image", response_model=schema.PlaceImageResponse)
async def get_place_image(id: int, db: Session = Depends(get_db)):
    image_url = await service.get_place_image(db=db, place_id=id)
    return {"image_url": image_url}

@router.post(
    "/places/{id}/reviews",
    response_model=schema.ReviewResponse,
    dependencies=[Depends(rate_limit(limit=10, window_seconds=60))],
)
def add_review(
    id: int,
    review: schema.ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = service.create_place_review(db=db, place_id=id, review_data=review, user=current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return result

@router.get("/places/{id}/reviews", response_model=list[schema.ReviewResponse])
def get_reviews(id: int, db: Session = Depends(get_db)):
    return service.get_place_reviews(db=db, place_id=id)
