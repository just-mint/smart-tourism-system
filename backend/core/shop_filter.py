import json
import math
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data.json"


def normalize_text(text):
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = " ".join(text.split())
    return text


def load_shops():
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        shops = json.load(file)
    return shops


def find_shop_by_id(shop_id):
    shops = load_shops()

    for shop in shops:
        if shop.get("id") == shop_id:
            return shop

    return None


def filter_shops_by_keywords(keywords):
    if isinstance(keywords, str):
        keywords = [keywords]

    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
        if str(keyword).strip()
    ]

    if not normalized_keywords:
        return []

    shops = load_shops()
    matched_shops = []

    for shop in shops:
        searchable_text = " ".join([
            shop.get("name", ""),
            shop.get("description", ""),
            shop.get("items", ""),
            " ".join(shop.get("keywords", []))
        ])

        searchable_text = normalize_text(searchable_text)

        if any(keyword in searchable_text for keyword in normalized_keywords):
            matched_shops.append(shop)

    return matched_shops


def calculate_distance_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = earth_radius * c

    return round(distance, 3)


def convert_shops_for_member_e(shops, user_lat=None, user_lon=None):
    converted = []

    for shop in shops:
        lat = shop["coords"]["lat"]
        lng = shop["coords"]["lng"]

        if user_lat is not None and user_lon is not None:
            distance_to_user = calculate_distance_km(user_lat, user_lon, lat, lng)
        else:
            distance_to_user = 0.0

        converted.append({
            "id": shop["id"],
            "name": shop["name"],
            "lat": lat,
            "lon": lng,
            "price": float(shop["price"]),
            "rating": float(shop["rating"]),
            "distance_to_user": distance_to_user
        })

    return converted