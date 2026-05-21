"""
AEGIS O2O - OSM-aware store and verified product seeder.

Goals:
  1. Promote only real OSM Places into Stores.
  2. Classify each store into a strict retail kind.
  3. Seed only products that have a product-specific image URL.
  4. Assign products to matching store kinds with global de-duplication.

External sources:
  - Open Food Facts API for packaged food/grocery products with real image_url.
  - DummyJSON product API for development-safe apparel/home/grocery products.

The seeder is deterministic-ish but not destructive: it updates/creates stores for
eligible places and rebuilds inventory rows for those stores only.
"""

from __future__ import annotations

import logging
import os
import random
import re
import sys
from dataclasses import dataclass
from typing import Any

import requests
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.domains.culture.model import Place
from app.domains.inventory.model import Inventory, Product, Store

logger = logging.getLogger(__name__)

STORE_KIND_FOOD = "food"
STORE_KIND_CLOTHING = "clothing"
STORE_KIND_SOUVENIR = "souvenir"
STORE_KIND_SUPERMARKET = "supermarket"
STORE_KIND_ATTRACTION = "attraction"
STORE_KIND_GENERIC = "store"

PRODUCTS_PER_STORE = {
    STORE_KIND_FOOD: (4, 7),
    STORE_KIND_CLOTHING: (4, 8),
    STORE_KIND_SOUVENIR: (4, 8),
    STORE_KIND_SUPERMARKET: (6, 12),
    STORE_KIND_GENERIC: (3, 6),
}

PRICE_RANGES_VND = {
    STORE_KIND_FOOD: (25_000, 120_000),
    STORE_KIND_CLOTHING: (180_000, 1_800_000),
    STORE_KIND_SOUVENIR: (50_000, 750_000),
    STORE_KIND_SUPERMARKET: (15_000, 350_000),
    STORE_KIND_GENERIC: (60_000, 900_000),
}

PLACE_CATEGORY_ALLOWLIST = {
    "Ẩm thực địa phương",
    "Mua sắm & Chợ",
    "Giải trí & Công viên",
    "Điểm tham quan & Di tích",
}

ATTRACTION_PLACE_CATEGORIES = {
    "Giải trí & Công viên",
    "Điểm tham quan & Di tích",
}

ATTRACTION_KEYWORDS = (
    "tourism",
    "attraction",
    "museum",
    "zoo",
    "theme_park",
    "leisure",
    "park",
    "garden",
    "historic",
    "bảo tàng",
    "công viên",
    "thảo cầm viên",
    "di tích",
    "lăng",
    "đền",
    "chùa",
    "thắng cảnh",
)

FOOD_KEYWORDS = (
    "amenity",
    "cafe",
    "restaurant",
    "fast_food",
    "bar",
    "pub",
    "food_court",
    "coffee",
    "cà phê",
    "tra sua",
    "trà sữa",
    "tea",
    "trà",
    "nhà hàng",
    "quán ăn",
    "bistro",
    "bakery",
    "bánh",
    "phở",
    "bún",
    "cơm",
    "mì",
    "juice",
    "sinh tố",
    "nước",
)
CLOTHING_KEYWORDS = (
    "shop",
    "fashion",
    "boutique",
    "clothing",
    "apparel",
    "thời trang",
    "quần áo",
    "áo dài",
    "lụa",
    "tailor",
    "shirt",
    "dress",
    "jacket",
)
SOUVENIR_KEYWORDS = (
    "souvenir",
    "gift",
    "craft",
    "handmade",
    "lưu niệm",
    "quà",
    "thủ công",
    "mỹ nghệ",
    "gốm",
    "tranh",
    "đèn lồng",
    "nón lá",
)
SUPERMARKET_KEYWORDS = (
    "marketplace",
    "supermarket",
    "convenience",
    "grocery",
    "mart",
    "minimart",
    "market",
    "chợ",
    "siêu thị",
    "bách hóa",
    "circle k",
    "winmart",
    "familymart",
)

CATEGORY_ALIASES = {
    "đặc sản": STORE_KIND_FOOD,
    "dac san": STORE_KIND_FOOD,
    "food": STORE_KIND_FOOD,
    "ẩm thực": STORE_KIND_FOOD,
    "am thuc": STORE_KIND_FOOD,
    "quần áo lụa": STORE_KIND_CLOTHING,
    "quan ao lua": STORE_KIND_CLOTHING,
    "clothing": STORE_KIND_CLOTHING,
    "fashion": STORE_KIND_CLOTHING,
    "apparel": STORE_KIND_CLOTHING,
    "đồ lưu niệm": STORE_KIND_SOUVENIR,
    "do luu niem": STORE_KIND_SOUVENIR,
    "souvenir": STORE_KIND_SOUVENIR,
    "craft": STORE_KIND_SOUVENIR,
    "supermarket": STORE_KIND_SUPERMARKET,
    "groceries": STORE_KIND_SUPERMARKET,
    "store": STORE_KIND_GENERIC,
}


@dataclass(frozen=True)
class ProductSeed:
    name: str
    category: str
    price: int
    image_url: str
    description: str
    source: str
    source_id: str | None = None


CURATED_PRODUCTS: tuple[ProductSeed, ...] = (
    ProductSeed(
        "Cà phê sữa đá Việt Nam",
        STORE_KIND_FOOD,
        45_000,
        "https://upload.wikimedia.org/wikipedia/commons/0/0c/Ca_phe_sua_da.jpg",
        "Ly cà phê sữa đá kiểu Việt Nam, phù hợp quán cà phê và điểm dừng ăn uống.",
        "wikimedia-commons",
        "Ca_phe_sua_da.jpg",
    ),
    ProductSeed(
        "Phở bò tô nóng",
        STORE_KIND_FOOD,
        75_000,
        "https://upload.wikimedia.org/wikipedia/commons/5/53/Pho-Beef-Noodles-2008.jpg",
        "Món phở bò phục vụ tại nhà hàng/quán ăn địa phương.",
        "wikimedia-commons",
        "Pho-Beef-Noodles-2008.jpg",
    ),
    ProductSeed(
        "Bánh mì Việt Nam",
        STORE_KIND_FOOD,
        35_000,
        "https://upload.wikimedia.org/wikipedia/commons/0/0c/B%C3%A1nh_m%C3%AC_th%E1%BB%8Bt_n%C6%B0%E1%BB%9Bng.png",
        "Bánh mì thịt nướng dùng cho nhóm cửa hàng ăn nhanh/quán địa phương.",
        "wikimedia-commons",
        "Bánh_mì_thịt_nướng.png",
    ),
    ProductSeed(
        "Trà sen nóng",
        STORE_KIND_FOOD,
        55_000,
        "https://upload.wikimedia.org/wikipedia/commons/4/45/Green_tea_3_appearances.jpg",
        "Trà sen/trà xanh phục vụ trong quán trà, cà phê và nhà hàng nhẹ.",
        "wikimedia-commons",
        "Green_tea_3_appearances.jpg",
    ),
    ProductSeed(
        "Áo dài truyền thống",
        STORE_KIND_CLOTHING,
        1_200_000,
        "https://upload.wikimedia.org/wikipedia/commons/3/3f/Ao_dai.jpg",
        "Trang phục áo dài dành cho boutique thời trang và cửa hàng lụa.",
        "wikimedia-commons",
        "Ao_dai.jpg",
    ),
    ProductSeed(
        "Áo sơ mi nam cotton",
        STORE_KIND_CLOTHING,
        420_000,
        "https://cdn.dummyjson.com/product-images/mens-shirts/man-plaid-shirt/thumbnail.webp",
        "Áo sơ mi nam cotton cho cửa hàng quần áo phổ thông.",
        "dummyjson",
        "mens-shirts/man-plaid-shirt",
    ),
    ProductSeed(
        "Đầm nữ dáng dài",
        STORE_KIND_CLOTHING,
        680_000,
        "https://cdn.dummyjson.com/product-images/womens-dresses/women-striped-dress/thumbnail.webp",
        "Đầm nữ thời trang cho boutique và cửa hàng apparel.",
        "dummyjson",
        "womens-dresses/women-striped-dress",
    ),
    ProductSeed(
        "Túi xách nữ da mềm",
        STORE_KIND_CLOTHING,
        850_000,
        "https://cdn.dummyjson.com/product-images/womens-bags/blue-women%27s-handbag/thumbnail.webp",
        "Túi xách thời trang dành cho cửa hàng boutique.",
        "dummyjson",
        "womens-bags/blue-womens-handbag",
    ),
    ProductSeed(
        "Nón lá Việt Nam",
        STORE_KIND_SOUVENIR,
        180_000,
        "https://upload.wikimedia.org/wikipedia/commons/a/a6/Non_la.jpg",
        "Nón lá quà lưu niệm Việt Nam cho cửa hàng thủ công/quà tặng.",
        "wikimedia-commons",
        "Non_la.jpg",
    ),
    ProductSeed(
        "Đèn lồng Hội An",
        STORE_KIND_SOUVENIR,
        220_000,
        "https://upload.wikimedia.org/wikipedia/commons/5/53/Hoi_An_lanterns.jpg",
        "Đèn lồng trang trí phong cách Hội An cho cửa hàng lưu niệm.",
        "wikimedia-commons",
        "Hoi_An_lanterns.jpg",
    ),
    ProductSeed(
        "Xích đu trang trí decor",
        STORE_KIND_SOUVENIR,
        360_000,
        "https://cdn.dummyjson.com/product-images/home-decoration/decoration-swing/thumbnail.webp",
        "Đồ decor nhà cửa phù hợp nhóm craft/home decor.",
        "dummyjson",
        "home-decoration/decoration-swing",
    ),
    ProductSeed(
        "Chậu cây trang trí để bàn",
        STORE_KIND_SOUVENIR,
        520_000,
        "https://cdn.dummyjson.com/product-images/home-decoration/house-showpiece-plant/thumbnail.webp",
        "Vật phẩm decor/quà tặng cho cửa hàng lưu niệm.",
        "dummyjson",
        "home-decoration/house-showpiece-plant",
    ),
    ProductSeed(
        "Kem hộp bán lẻ",
        STORE_KIND_SUPERMARKET,
        12_000,
        "https://cdn.dummyjson.com/product-images/groceries/ice-cream/thumbnail.webp",
        "Thực phẩm lạnh bán lẻ dùng cho siêu thị/cửa hàng tiện lợi.",
        "dummyjson",
        "groceries/ice-cream",
    ),
    ProductSeed(
        "Sữa tươi đóng hộp",
        STORE_KIND_SUPERMARKET,
        38_000,
        "https://cdn.dummyjson.com/product-images/groceries/milk/thumbnail.webp",
        "Sữa và đồ uống đóng gói cho siêu thị/cửa hàng tiện lợi.",
        "dummyjson",
        "groceries/milk",
    ),
    ProductSeed(
        "Mì Ý đóng gói",
        STORE_KIND_SUPERMARKET,
        48_000,
        "https://cdn.dummyjson.com/product-images/groceries/spaghetti-pasta/thumbnail.webp",
        "Thực phẩm khô đóng gói dành cho cửa hàng grocery.",
        "dummyjson",
        "groceries/spaghetti-pasta",
    ),
    ProductSeed(
        "Son môi đỏ",
        STORE_KIND_SUPERMARKET,
        95_000,
        "https://cdn.dummyjson.com/product-images/beauty/red-lipstick/thumbnail.webp",
        "Mỹ phẩm chăm sóc cá nhân cho siêu thị mini/cửa hàng tiện lợi.",
        "dummyjson",
        "beauty/red-lipstick",
    ),
)


def clean_product_name(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = text.replace("�", "")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    return text[:255]


def normalize(value: str | None) -> str:
    return clean_product_name(value or "").casefold()


def has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def normalize_category_alias(category: str | None) -> str | None:
    key = normalize(category)
    return CATEGORY_ALIASES.get(key)


def classify_store(place: Place) -> str | None:
    if not place.category or place.category not in PLACE_CATEGORY_ALLOWLIST:
        return None

    text = normalize(" ".join([place.name or "", place.category or "", place.address or ""]))

    # STRICT HIERARCHICAL ORDER
    # 1. ATTRACTIONS (parks, museums, historic sites)
    if has_any_keyword(text, ATTRACTION_KEYWORDS) or place.category in ATTRACTION_PLACE_CATEGORIES:
        return STORE_KIND_ATTRACTION

    # 2. FOOD (cafes, restaurants, food courts)
    if has_any_keyword(text, FOOD_KEYWORDS) or place.category == "Ẩm thực địa phương":
        return STORE_KIND_FOOD

    # 3. SHOPPING
    if has_any_keyword(text, SUPERMARKET_KEYWORDS):
        return STORE_KIND_SUPERMARKET
    if has_any_keyword(text, CLOTHING_KEYWORDS):
        return STORE_KIND_CLOTHING
    if has_any_keyword(text, SOUVENIR_KEYWORDS):
        return STORE_KIND_SOUVENIR

    # Fallback for generic shopping places
    if place.category == "Mua sắm & Chợ":
        return STORE_KIND_SUPERMARKET if "chợ" in text or "market" in text else STORE_KIND_SOUVENIR

    return STORE_KIND_GENERIC


def price_for_category(category: str, seed_price: int | None = None) -> int:
    low, high = PRICE_RANGES_VND.get(category, PRICE_RANGES_VND[STORE_KIND_GENERIC])
    if seed_price and low <= seed_price <= high:
        base = seed_price
    else:
        base = random.randint(low, high)
    rounded = max(low, min(high, int(base * random.uniform(0.94, 1.08))))
    return int(round(rounded / 1_000) * 1_000)


def product_seed_from_dummyjson(raw: dict[str, Any], category: str) -> ProductSeed | None:
    name = clean_product_name(str(raw.get("title") or ""))
    image_url = raw.get("thumbnail") or next(iter(raw.get("images") or []), None)
    if not name or not image_url:
        return None

    usd_price = float(raw.get("price") or 0)
    estimated_vnd = int(usd_price * 25_000) if usd_price > 0 else None
    price = price_for_category(category, estimated_vnd)
    return ProductSeed(
        name=name,
        category=category,
        price=price,
        image_url=str(image_url),
        description=clean_product_name(str(raw.get("description") or f"Sản phẩm {name}.")),
        source="dummyjson",
        source_id=str(raw.get("id")) if raw.get("id") else None,
    )


def fetch_dummyjson_products() -> list[ProductSeed]:
    category_map = {
        "mens-shirts": STORE_KIND_CLOTHING,
        "womens-dresses": STORE_KIND_CLOTHING,
        "womens-bags": STORE_KIND_CLOTHING,
        "home-decoration": STORE_KIND_SOUVENIR,
        "groceries": STORE_KIND_SUPERMARKET,
        "beauty": STORE_KIND_SUPERMARKET,
    }
    seeds: list[ProductSeed] = []
    for remote_category, local_category in category_map.items():
        url = f"https://dummyjson.com/products/category/{remote_category}"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("DummyJSON fetch failed for %s: %s", remote_category, exc)
            continue
        for raw in response.json().get("products", []):
            seed = product_seed_from_dummyjson(raw, local_category)
            if seed:
                seeds.append(seed)
    return seeds


def product_seed_from_openfoodfacts(raw: dict[str, Any], category: str) -> ProductSeed | None:
    name = clean_product_name(str(raw.get("product_name") or raw.get("product_name_en") or ""))
    image_url = raw.get("image_url") or raw.get("image_front_url")
    if not name or not image_url:
        return None

    brands = clean_product_name(str(raw.get("brands") or ""))
    display_name = clean_product_name(f"{brands} {name}" if brands else name)
    code = str(raw.get("code") or "") or None
    return ProductSeed(
        name=display_name,
        category=category,
        price=price_for_category(category),
        image_url=str(image_url),
        description="Sản phẩm đóng gói có ảnh sản phẩm thật từ Open Food Facts.",
        source="openfoodfacts",
        source_id=code,
    )


def fetch_openfoodfacts_products() -> list[ProductSeed]:
    queries = {
        STORE_KIND_SUPERMARKET: ["milk", "instant noodles", "coffee", "snack", "juice"],
        STORE_KIND_FOOD: ["coffee", "tea", "juice"],
    }
    seeds: list[ProductSeed] = []
    headers = {"User-Agent": "AEGIS-O2O/1.0 product-seeder (local development)"}
    for category, terms in queries.items():
        for term in terms:
            try:
                response = requests.get(
                    "https://world.openfoodfacts.org/cgi/search.pl",
                    params={
                        "search_terms": term,
                        "search_simple": 1,
                        "action": "process",
                        "json": 1,
                        "page_size": 8,
                        "fields": "code,product_name,product_name_en,brands,image_url,image_front_url",
                    },
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("Open Food Facts fetch failed for %s: %s", term, exc)
                continue
            for raw in response.json().get("products", []):
                seed = product_seed_from_openfoodfacts(raw, category)
                if seed:
                    seeds.append(seed)
    return seeds


def load_product_catalog() -> list[ProductSeed]:
    catalog = list(CURATED_PRODUCTS)
    if os.getenv("AEGIS_FETCH_PRODUCT_SOURCES", "1") != "0":
        catalog.extend(fetch_openfoodfacts_products())
        catalog.extend(fetch_dummyjson_products())

    deduped: dict[tuple[str, str], ProductSeed] = {}
    for seed in catalog:
        if not seed.image_url:
            continue
        clean_name = clean_product_name(seed.name)
        if not clean_name:
            continue
        key = (seed.category, normalize(clean_name))
        deduped.setdefault(
            key,
            ProductSeed(
                name=clean_name,
                category=seed.category,
                price=price_for_category(seed.category, seed.price),
                image_url=seed.image_url,
                description=seed.description,
                source=seed.source,
                source_id=seed.source_id,
            ),
        )

    seeds = list(deduped.values())
    missing_images = [seed.name for seed in seeds if not seed.image_url]
    if missing_images:
        raise RuntimeError(f"Product catalog contains items without images: {missing_images[:5]}")
    logger.info("Verified product catalog loaded: %d products", len(seeds))
    return seeds


def upsert_products(db: Session, seeds: list[ProductSeed]) -> dict[str, list[Product]]:
    products_by_category: dict[str, list[Product]] = {
        STORE_KIND_FOOD: [],
        STORE_KIND_CLOTHING: [],
        STORE_KIND_SOUVENIR: [],
        STORE_KIND_SUPERMARKET: [],
        STORE_KIND_GENERIC: [],
    }
    existing = {normalize(p.name): p for p in db.query(Product).all()}

    for seed in seeds:
        product = existing.get(normalize(seed.name))
        original_price = int(seed.price * random.uniform(1.08, 1.28))
        source_note = f"Nguồn ảnh: {seed.source}"
        description = seed.description
        if seed.source_id:
            description = f"{description} ({source_note}, id: {seed.source_id})"
        else:
            description = f"{description} ({source_note})"

        if product is None:
            product = Product(name=seed.name)
            db.add(product)
            existing[normalize(seed.name)] = product

        product.category = seed.category
        product.price = seed.price
        product.original_price = original_price
        product.image_url = seed.image_url
        product.description = description
        products_by_category.setdefault(seed.category, []).append(product)

    db.flush()
    for products in products_by_category.values():
        products.sort(key=lambda p: p.product_id or 0)
    return products_by_category


def product_pool_for_store(
    store_category: str,
    products_by_category: dict[str, list[Product]],
) -> list[Product]:
    if store_category == STORE_KIND_GENERIC:
        return (
            products_by_category.get(STORE_KIND_CLOTHING, [])
            + products_by_category.get(STORE_KIND_SOUVENIR, [])
            + products_by_category.get(STORE_KIND_SUPERMARKET, [])
        )
    return products_by_category.get(store_category, [])


def pick_products_for_store(
    store_category: str,
    pool: list[Product],
    assigned_product_ids: set[int],
) -> list[Product]:
    if not pool:
        return []
    low, high = PRODUCTS_PER_STORE.get(store_category, PRODUCTS_PER_STORE[STORE_KIND_GENERIC])
    wanted = random.randint(low, min(high, max(low, len(pool))))
    unique_pool = [p for p in pool if p.product_id not in assigned_product_ids]
    source_pool = unique_pool if len(unique_pool) >= wanted else pool[:]
    random.shuffle(source_pool)
    chosen = source_pool[: min(wanted, len(source_pool))]
    assigned_product_ids.update(p.product_id for p in chosen if p.product_id is not None)
    return chosen


def create_or_update_store(db: Session, place: Place, store_category: str) -> tuple[Store, bool]:
    existing = db.query(Store).filter(Store.place_id == str(place.place_id)).one_or_none()
    lat = float(place.lat)
    lon = float(place.lon)
    geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

    if existing:
        store = existing
        created = False
    else:
        store = Store(place_id=str(place.place_id))
        db.add(store)
        created = True

    store.name = place.name.strip()
    store.category = store_category
    store.address = place.address or f"Tọa độ: {lat:.5f}, {lon:.5f}"
    store.lat = lat
    store.lon = lon
    store.geom = geom
    if store.rating is None:
        store.rating = round(random.uniform(3.7, 5.0), 1)
    return store, created


def main() -> None:
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()

    try:
        places = db.query(Place).all()
        if not places:
            logger.info("No places found. Ensure places are seeded first.")
            return

        product_seeds = load_product_catalog()
        products_by_category = upsert_products(db, product_seeds)

        eligible_places: list[tuple[Place, str]] = []
        skipped = {"no_name": 0, "no_coords": 0, "bad_category": 0}
        for place in places:
            if not place.name or not place.name.strip():
                skipped["no_name"] += 1
                continue
            if not place.lat or not place.lon:
                skipped["no_coords"] += 1
                continue
            store_category = classify_store(place)
            if not store_category:
                skipped["bad_category"] += 1
                continue
            eligible_places.append((place, store_category))

        logger.info(
            "Eligible O2O places: %d (skipped: %s)",
            len(eligible_places),
            skipped,
        )

        stores_created = 0
        stores_updated = 0
        inventory_created = 0
        assigned_product_ids: set[int] = set()

        for index, (place, store_category) in enumerate(eligible_places, start=1):
            store, created = create_or_update_store(db, place, store_category)
            db.flush()

            if created:
                stores_created += 1
            else:
                stores_updated += 1

            db.query(Inventory).filter(Inventory.store_id == store.store_id).delete(
                synchronize_session=False
            )

            if store_category != STORE_KIND_ATTRACTION:
                pool = product_pool_for_store(store_category, products_by_category)
                chosen = pick_products_for_store(store_category, pool, assigned_product_ids)
                for product in chosen:
                    db.add(
                        Inventory(
                            store_id=store.store_id,
                            product_id=product.product_id,
                            stock=random.randint(8, 120),
                            price_override=price_for_category(
                                store_category,
                                product.price,
                            ),
                        )
                    )
                    inventory_created += 1

            if index % 200 == 0:
                db.commit()
                logger.info("Committed %d/%d eligible places", index, len(eligible_places))

        db.commit()

        totals_by_category = {
            category: db.query(Store).filter(Store.category == category).count()
            for category in [
                STORE_KIND_FOOD,
                STORE_KIND_CLOTHING,
                STORE_KIND_SOUVENIR,
                STORE_KIND_SUPERMARKET,
                STORE_KIND_ATTRACTION,
                STORE_KIND_GENERIC,
            ]
        }
        products_without_images = (
            db.query(Product)
            .filter((Product.image_url.is_(None)) | (Product.image_url == ""))
            .count()
        )

        logger.info("=" * 72)
        logger.info("AEGIS O2O seeding report")
        logger.info("Stores created: %d", stores_created)
        logger.info("Stores updated: %d", stores_updated)
        logger.info("Inventory rows rebuilt: %d", inventory_created)
        logger.info("Store categories: %s", totals_by_category)
        logger.info("Products without image_url in DB: %d", products_without_images)
        logger.info("=" * 72)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    main()
