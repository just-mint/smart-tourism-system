import logging
from datetime import datetime

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.culture import schema
from app.domains.culture.model import Place, Review

logger = logging.getLogger(__name__)
_story_cache: dict[tuple[int, str], str] = {}
_image_cache: dict[int, str | None] = {}


def search_places_by_name(db: Session, keyword: str):
    if not keyword or len(keyword.strip()) < 2:
        return []
    # Dùng ilike cho tìm kiếm full-text
    safe_keyword = keyword.strip()
    return db.query(Place).filter(Place.name.ilike(f"%{safe_keyword}%")).limit(20).all()

async def generate_place_story(db: Session, place_id: int):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None

    # Lập Prompt theo đúng yêu cầu
    prompt = f"Bạn là hướng dẫn viên du lịch, hãy kể một câu chuyện ngắn 100 từ về {place.name} thuộc loại hình {place.category or 'văn hóa'} cho du khách."

    api_key = settings.GEMINI_API_KEY
    # Nội dung Fallback cứng phòng trường hợp Timeout hoặc LLM API bị sập
    bot_story = f"[{place.name}] là một biểu tượng nổi bật thuộc nhóm {place.category or 'văn hóa'}. Nơi đây lưu giữ nhiều giá trị lịch sử và không gian nghệ thuật chờ bạn khám phá trên bản đồ AEGIS."
    cache_key = (place_id, "vi:v1")
    if cache_key in _story_cache:
        bot_story = _story_cache[cache_key]
        return {"id": place.id, "place_id": place.place_id, "name": place.name, "category": place.category, "address": place.address, "lat": place.lat, "lon": place.lon, "ai_story": bot_story}

    if api_key:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            # Timeout 10 giây để đảm bảo nhận đủ text từ Gemini
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers={"x-goog-api-key": api_key})
                if response.status_code == 200:
                    resp_data = response.json()
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts and "text" in parts[0]:
                            bot_story = parts[0]["text"]
                else:
                    logger.warning("Gemini story request failed: status=%s", response.status_code)
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("Gemini story request failed: %s", exc)

    _story_cache[cache_key] = bot_story
    return {"id": place.id, "place_id": place.place_id, "name": place.name, "category": place.category, "address": place.address, "lat": place.lat, "lon": place.lon, "ai_story": bot_story}


async def generate_store_place_story(db: Session, store_id: int):
    from app.domains.inventory.model import Store

    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store or not store.place_id:
        return None
    place = db.query(Place).filter(Place.place_id == str(store.place_id)).first()
    if not place:
        return None
    return await generate_place_story(db, place.id)


async def get_place_image(db: Session, place_id: int) -> str | None:
    if place_id in _image_cache:
        return _image_cache[place_id]

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None
    if place.image_url:
        _image_cache[place_id] = place.image_url
        return place.image_url

    async def fetch_thumbnail(title: str) -> str | None:
        url = "https://vi.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": "1200",
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", {})
            if not pages:
                return None
            first = next(iter(pages.values()))
            return first.get("thumbnail", {}).get("source")

    try:
        image_url = await fetch_thumbnail(place.name)
    except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
        logger.warning("Wikipedia image lookup failed for place_id=%s: %s", place_id, exc)
        image_url = None

    _image_cache[place_id] = image_url
    return image_url

def create_place_review(db: Session, place_id: int, review_data: schema.ReviewCreate, user=None):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None

    bad_words = ["tệ", "xấu", "lừa đảo", "chửi", "ngu"]
    content_lower = review_data.text.lower()
    if any(word in content_lower for word in bad_words):
        raise HTTPException(status_code=400, detail="Nội dung đánh giá chứa từ ngữ không phù hợp.")

    author_name = user.full_name if user and user.full_name else (review_data.author_name or "Khách tham quan")
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
    if not place:
        return []
    return db.query(Review).filter(Review.place_id == str(place.place_id)).all()
