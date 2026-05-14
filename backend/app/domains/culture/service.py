from sqlalchemy.orm import Session
from sqlalchemy import func
from app.domains.culture.model import Place, Review
from app.domains.culture import schema
import httpx
from datetime import datetime
import os
import json
from redis.asyncio import Redis
from app.models import User
from app.domains.inventory.model import Store

def search_places_by_name(db: Session, keyword: str):
    # Dùng ilike cho tìm kiếm full-text
    return db.query(Place).filter(Place.name.ilike(f"%{keyword}%")).limit(20).all()


def get_culture_metadata(db: Session):
    total_places = db.query(func.count(Place.id)).scalar() or 0
    total_categories = (
        db.query(func.count(func.distinct(Place.category)))
        .filter(Place.category.isnot(None))
        .scalar()
        or 0
    )
    total_stores = db.query(func.count(Store.store_id)).scalar() or 0
    approved_reviews = (
        db.query(func.count(Review.id)).filter(Review.status == "approved").scalar() or 0
    )
    return {
        "total_places": total_places,
        "total_categories": total_categories,
        "total_stores": total_stores,
        "approved_reviews": approved_reviews,
    }


def _fallback_image_for_category(category: str | None) -> str | None:
    normalized = (category or "").lower()
    if "ẩm" in normalized or "food" in normalized:
        return None
    if "chợ" in normalized or "shopping" in normalized:
        return None
    if "công viên" in normalized or "park" in normalized:
        return None
    return None


async def get_wikipedia_image(title: str, category: str | None = None):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_key = f"wiki:image:{title.strip().lower()}"
    redis: Redis | None = None
    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        cached = await redis.get(cache_key)
        if cached:
            result = json.loads(cached)
            await redis.aclose()
            return result
    except Exception:
        redis = None

    fallback = {"image_url": _fallback_image_for_category(category), "source": "fallback"}
    if not title.strip():
        return fallback

    result = fallback
    try:
        async with httpx.AsyncClient(
            timeout=6.0,
            headers={"User-Agent": "AEGIS-O2O/1.0 (culture-image-proxy)"},
        ) as client:
            params = {
                "action": "query",
                "origin": "*",
                "titles": title,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 1200,
            }
            response = await client.get("https://vi.wikipedia.org/w/api.php", params=params)
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", {})
            image_url = None
            if pages:
                page = next(iter(pages.values()))
                image_url = page.get("thumbnail", {}).get("source")

            if not image_url:
                search_response = await client.get(
                    "https://vi.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "origin": "*",
                        "list": "search",
                        "srsearch": title,
                        "utf8": "",
                        "format": "json",
                    },
                )
                search_response.raise_for_status()
                matches = search_response.json().get("query", {}).get("search", [])
                if matches:
                    best_title = matches[0].get("title")
                    image_response = await client.get(
                        "https://vi.wikipedia.org/w/api.php",
                        params={
                            "action": "query",
                            "origin": "*",
                            "titles": best_title,
                            "prop": "pageimages",
                            "format": "json",
                            "pithumbsize": 1200,
                        },
                    )
                    image_response.raise_for_status()
                    pages = image_response.json().get("query", {}).get("pages", {})
                    if pages:
                        page = next(iter(pages.values()))
                        image_url = page.get("thumbnail", {}).get("source")

            if image_url:
                result = {"image_url": image_url, "source": "wikipedia"}
    except Exception:
        result = fallback

    if redis:
        try:
            await redis.set(cache_key, json.dumps(result), ex=60 * 60 * 24)
            await redis.aclose()
        except Exception:
            pass
    return result

async def generate_place_story(db: Session, place_id: int):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place: return None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_key = f"culture:story:{place.id}"
    redis: Redis | None = None
    try:
        redis = Redis.from_url(redis_url, decode_responses=True)
        cached = await redis.get(cache_key)
        if cached:
            cached_payload = json.loads(cached)
            cached_payload["story_cached"] = True
            await redis.aclose()
            return cached_payload
    except Exception:
        redis = None
    
    # Lập Prompt theo đúng yêu cầu
    prompt = f"Bạn là hướng dẫn viên du lịch, hãy kể một câu chuyện ngắn 100 từ về {place.name} thuộc loại hình {place.category or 'văn hóa'} cho du khách."
    
    from app.core.config import settings
    api_key = settings.GEMINI_API_KEY
    # Nội dung Fallback cứng phòng trường hợp Timeout hoặc LLM API bị sập
    bot_story = f"[{place.name}] là một biểu tượng nổi bật thuộc nhóm {place.category or 'văn hóa'}. Nơi đây lưu giữ nhiều giá trị lịch sử và không gian nghệ thuật chờ bạn khám phá trên bản đồ AEGIS."
    
    story_source = "fallback"

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
                            story_source = "gemini-2.5-flash"
        except Exception:
            # Rơi vào Rate-limit hoặc Timeout -> Im lặng xài bot_story Fallback
            pass
            
    images = [place.image_url] if place.image_url else []
    image_source = "place.image_url" if place.image_url else None
    result = {
        "id": place.id,
        "place_id": place.place_id,
        "name": place.name,
        "category": place.category,
        "address": place.address,
        "lat": float(place.lat) if place.lat else 0.0,
        "lon": float(place.lon) if place.lon else 0.0,
        "rating": float(place.rating) if place.rating else None,
        "review_count": place.review_count,
        "ai_story": bot_story,
        "story_source": story_source,
        "story_cached": False,
        "content_sources": ["AEGIS places dataset", story_source],
        "opening_hours": None,
        "ticket_price": None,
        "rules": [
            "Giữ gìn vệ sinh và tuân thủ hướng dẫn tại điểm đến.",
            "Kiểm tra giờ mở cửa và giá vé chính thức trước khi khởi hành.",
        ],
        "images": images,
        "image_source": image_source,
    }

    if redis:
        try:
            await redis.set(cache_key, json.dumps(result, default=str), ex=60 * 60 * 24)
            await redis.aclose()
        except Exception:
            pass

    return result

def _review_author_name(user: User) -> str:
    return user.full_name or user.email.split("@")[0]


def create_place_review(db: Session, place_id: int, review_data: schema.ReviewCreate, user: User):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return None
    time_str = datetime.now().isoformat()
    review = Review(
        place_id=str(place.place_id), 
        user_id=user.id,
        author_name=_review_author_name(user),
        rating=review_data.rating,
        text=review_data.text,
        time_posted=time_str,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

def get_place_reviews(db: Session, place_id: int, include_unapproved: bool = False):
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place: return []
    query = db.query(Review).filter(Review.place_id == str(place.place_id))
    if not include_unapproved:
        query = query.filter(Review.status == "approved")
    return query.order_by(Review.id.desc()).all()


def list_reviews_for_moderation(db: Session, status: str = "pending"):
    query = db.query(Review)
    if status != "all":
        query = query.filter(Review.status == status)
    return query.order_by(Review.id.desc()).limit(200).all()


def moderate_review(
    db: Session,
    review_id: int,
    data: schema.ReviewModerationUpdate,
    moderator: User,
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        return None
    review.status = data.status
    review.moderation_note = data.moderation_note
    review.moderated_by = moderator.id
    review.moderated_at = datetime.now()
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def report_review(db: Session, review_id: int, data: schema.ReviewReportCreate):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        return None
    review.report_count = (review.report_count or 0) + 1
    review.report_reason = data.reason
    review.reported_at = datetime.now()
    if review.status == "approved":
        review.status = "pending"
        review.moderation_note = "Auto-held for moderation after user report."
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
