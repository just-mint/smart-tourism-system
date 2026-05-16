
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.culture import schema, service
from app.domains.spatial.schema import PlaceResponse

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

@router.post("/places/{id}/reviews", response_model=schema.ReviewResponse)
def add_review(id: int, review: schema.ReviewCreate, db: Session = Depends(get_db)):
    result = service.create_place_review(db=db, place_id=id, review_data=review)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return result

@router.get("/places/{id}/reviews", response_model=list[schema.ReviewResponse])
def get_reviews(id: int, db: Session = Depends(get_db)):
    return service.get_place_reviews(db=db, place_id=id)
