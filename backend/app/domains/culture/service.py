from sqlalchemy.orm import Session
from app.domains.culture.model import Place, Review
from app.domains.culture import schema
import httpx
from datetime import datetime
import os
from fastapi import HTTPException

def search_places_by_name(db: Session, keyword: str):
    # Dùng ilike cho tìm kiếm full-text
    return db.query(Place).filter(Place.name.ilike(f"%{keyword}%")).limit(20).all()

async def generate_place_story(db: Session, place_id: int):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place: return None
    
    # Lập Prompt theo đúng yêu cầu
    prompt = f"Bạn là hướng dẫn viên du lịch, hãy kể một câu chuyện ngắn 100 từ về {place.name} thuộc loại hình {place.category or 'văn hóa'} cho du khách."
    
    from app.core.config import settings
    api_key = settings.GEMINI_API_KEY
    # Nội dung Fallback cứng phòng trường hợp Timeout hoặc LLM API bị sập
    bot_story = f"[{place.name}] là một biểu tượng nổi bật thuộc nhóm {place.category or 'văn hóa'}. Nơi đây lưu giữ nhiều giá trị lịch sử và không gian nghệ thuật chờ bạn khám phá trên bản đồ AEGIS."
    
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            # Timeout 10 giây để đảm bảo nhận đủ text từ Gemini
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    resp_data = response.json()
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts and "text" in parts[0]:
                            bot_story = parts[0]["text"]
        except Exception:
            # Rơi vào Rate-limit hoặc Timeout -> Im lặng xài bot_story Fallback
            pass
            
    return {"id": place.id, "place_id": place.place_id, "name": place.name, "category": place.category, "address": place.address, "lat": place.lat, "lon": place.lon, "ai_story": bot_story}

def create_place_review(db: Session, place_id: int, review_data: schema.ReviewCreate, user=None):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None
        
    bad_words = ["tệ", "xấu", "lừa đảo", "chửi", "ngu"]
    content_lower = review_data.text.lower()
    if any(word in content_lower for word in bad_words):
        raise HTTPException(status_code=400, detail="Nội dung đánh giá chứa từ ngữ không phù hợp.")

    author_name = user.full_name if user and user.full_name else review_data.author_name
    time_str = datetime.now().isoformat()
    review = Review(
        place_id=str(place.place_id), 
        author_name=author_name,
        rating=review_data.rating,
        text=review_data.text,
        time_posted=time_str
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

def get_place_reviews(db: Session, place_id: int):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place: return []
    return db.query(Review).filter(Review.place_id == str(place.place_id)).all()
