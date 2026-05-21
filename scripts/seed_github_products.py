#!/usr/bin/env python3
"""
=============================================================================
  AEGIS O2O — CONTEXT-AWARE PRODUCT SEEDING FROM GITHUB
=============================================================================
  Script: seed_github_products.py
  Author: AEGIS Data Engineering Team
  
  Tải dữ liệu sản phẩm thật từ Github repo:
    https://github.com/QuyenThang2011/Data_Travel_App/tree/main/Data
  
  Parse SQL INSERT statements, phân loại sản phẩm theo từ khóa,
  và gán vào Store phù hợp (Context-Aware, KHÔNG random bừa).
  
  Data sources:
    - quanao_data.sql  → Fashion / Clothing products + stores
    - dacsan_data.sql  → Specialty food / Regional products + stores
=============================================================================
"""

import re
import sys
import os
import random
import requests
from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

# ── Setup Python path for project imports ────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.session import SessionLocal
from app.domains.inventory.model import Store, Product, Inventory


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/QuyenThang2011/Data_Travel_App/main/Data"

DATA_FILES = {
    "quanao":  f"{GITHUB_RAW_BASE}/quanao_data.sql",
    "dacsan":  f"{GITHUB_RAW_BASE}/dacsan_data.sql",
}

BATCH_SIZE = 50  # Commit mỗi 50 records

# ── Keyword-based classification ─────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "TRADITIONAL": [
        "áo dài", "nón lá", "lụa", "gấm", "thổ cẩm", "mỹ nghệ",
        "truyền thống", "đặc sản", "mắm", "chè lam", "bánh ít",
        "bánh tráng", "nem", "mè xửng", "bánh dày", "bánh ép",
        "ô mai", "kẹo dừa", "cốm", "bánh hồng", "bánh nhãn",
        "bánh phồng", "lạp xưởng", "khô cá", "mắm cá", "mắm tép",
        "nước mắm", "tương ớt", "chả", "bún", "miến", "bánh canh",
        "thịt trâu", "thịt chua", "muối ớt", "chè tân cương",
        "bánh gạo", "bánh dừa", "khoai", "sấy dẻo", "sấy giòn",
        "cơm cháy", "đậu phộng", "tóp mỡ", "ruốc", "hải sản",
        "mực", "tôm", "cá", "bò khô", "gà sấy", "da heo",
        "bánh gio", "trà", "cà phê", "hạt điều", "hạt dẻ",
        "vùng miền", "quê hương", "cố đô", "xứ dừa", "tây bắc",
        "đà lạt", "huế", "đà nẵng", "nha trang", "phú quốc",
        "bến tre", "cà mau", "sapa", "hà giang", "bình định",
    ],
    "MODERN_FASHION": [
        "áo thun", "jeans", "jean", "khoác", "sneaker", "váy",
        "croptop", "hoodie", "polo", "sơ mi", "quần short",
        "unisex", "thể thao", "bigsize", "pijama", "pyjama",
        "đồ ngủ", "babydoll", "baby tee", "form rộng", "set đồ",
        "đồ bộ", "bộ quần áo", "cotton", "tổ ong", "waffle",
        "thun lạnh", "đũi", "linen", "kaki", "denim", "vải xốp",
        "thời trang", "fashion", "boutique", "closet", "studio",
        "clothing", "store", "shop", "trendy", "style",
        "quần áo", "set bộ", "áo phông", "quần đùi", "ống rộng",
        "ống suông", "tay lỡ", "cộc tay",
    ],
    "ACCESSORIES": [
        "túi xách", "kính", "mũ cói", "vali", "balo", "ví",
        "thắt lưng", "đồng hồ", "trang sức", "phụ kiện",
        "nón", "mũ", "giày", "dép", "sandal",
    ],
}

# ── Store category mapping for context-aware assignment ──────────────────
STORE_CATEGORY_MAP = {
    "TRADITIONAL": ["food"],                               # Đặc sản → food stores
    "MODERN_FASHION": ["store"],                           # Quần áo → store
    "ACCESSORIES": ["store"],                              # Phụ kiện → store
    "GENERAL": ["store", "food"],                          # Fallback
    "DACSAN_STORE": [],    # Sẽ gán trực tiếp từ file SQL
    "QUANAO_STORE": [],    # Sẽ gán trực tiếp từ file SQL
}


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 1: FETCH DATA FROM GITHUB
# ═══════════════════════════════════════════════════════════════════════════
def fetch_sql_from_github(url: str) -> str:
    """Tải nội dung file SQL từ Github Raw URL."""
    print(f"\n📡 Đang tải dữ liệu từ: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    content = resp.text
    line_count = content.count('\n')
    print(f"   ✅ Tải thành công: {len(content):,} bytes, ~{line_count:,} dòng")
    return content


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 2: PARSE SQL INSERT STATEMENTS
# ═══════════════════════════════════════════════════════════════════════════

# Regex patterns cho các loại INSERT
RE_STORE = re.compile(
    r"INSERT INTO stores\s*\(store_id,\s*name,\s*address,\s*geom,\s*place_id\)\s*"
    r"VALUES\s*\(\s*(\d+)\s*,\s*'((?:[^']|'')*?)'\s*,\s*(NULL|'(?:[^']|'')*?')\s*,\s*"
    r"ST_SetSRID\(ST_MakePoint\(([\d.\-]+),\s*([\d.\-]+)\),\s*4326\)\s*,\s*'((?:[^']|'')*?)'\s*\)",
    re.IGNORECASE
)

RE_PRODUCT = re.compile(
    r"INSERT INTO products\s*\(product_id,\s*name,\s*description,\s*price,\s*image_url\)\s*"
    r"VALUES\s*\(\s*(\d+)\s*,\s*'((?:[^']|'')*?)'\s*,\s*'((?:[^']|'')*?)'\s*,\s*(\d+)\s*,\s*'((?:[^']|'')*?)'\s*\)",
    re.IGNORECASE
)

RE_INVENTORY = re.compile(
    r"INSERT INTO inventory\s*\(inventory_id,\s*product_id,\s*store_id,\s*stock\)\s*"
    r"VALUES\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
    re.IGNORECASE
)


def parse_sql_data(sql_content: str, source_label: str):
    """Parse SQL file thành danh sách stores, products, inventory records."""
    stores = []
    products = []
    inventories = []

    for m in RE_STORE.finditer(sql_content):
        store_id = int(m.group(1))
        name = m.group(2).replace("''", "'")
        address = m.group(3)
        if address and address != "NULL":
            address = address.strip("'").replace("''", "'")
        else:
            address = None
        lon = float(m.group(4))
        lat = float(m.group(5))
        place_id = m.group(6).replace("''", "'")
        stores.append({
            "store_id": store_id,
            "name": name,
            "address": address,
            "lon": lon,
            "lat": lat,
            "place_id": place_id,
            "source": source_label,
        })

    for m in RE_PRODUCT.finditer(sql_content):
        product_id = int(m.group(1))
        name = m.group(2).replace("''", "'")
        description = m.group(3).replace("''", "'")
        price = int(m.group(4))
        image_url = m.group(5).replace("''", "'")
        products.append({
            "product_id": product_id,
            "name": name,
            "description": description,
            "price": price,
            "image_url": image_url,
            "source": source_label,
        })

    for m in RE_INVENTORY.finditer(sql_content):
        inv_id = int(m.group(1))
        product_id = int(m.group(2))
        store_id = int(m.group(3))
        stock = int(m.group(4))
        inventories.append({
            "inventory_id": inv_id,
            "product_id": product_id,
            "store_id": store_id,
            "stock": stock,
        })

    print(f"   📦 [{source_label}] Parsed: {len(stores)} stores, {len(products)} products, {len(inventories)} inventory records")
    return stores, products, inventories


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 3: CATEGORIZE PRODUCTS (RULE-BASED)
# ═══════════════════════════════════════════════════════════════════════════
def categorize_product(product_name: str, source: str) -> str:
    """Phân loại sản phẩm dựa trên từ khóa trong tên."""
    name_lower = product_name.lower()
    
    # Đặc sản luôn là TRADITIONAL
    if source == "dacsan":
        return "TRADITIONAL"
    
    # Kiểm tra từ khóa ACCESSORIES trước (ít phổ biến hơn)
    for kw in CATEGORY_KEYWORDS["ACCESSORIES"]:
        if kw.lower() in name_lower:
            return "ACCESSORIES"
    
    # Kiểm tra TRADITIONAL
    trad_score = sum(1 for kw in CATEGORY_KEYWORDS["TRADITIONAL"] if kw.lower() in name_lower)
    
    # Kiểm tra MODERN_FASHION
    modern_score = sum(1 for kw in CATEGORY_KEYWORDS["MODERN_FASHION"] if kw.lower() in name_lower)
    
    # Quần áo source mặc định là MODERN_FASHION
    if source == "quanao":
        if trad_score > modern_score and trad_score >= 2:
            return "TRADITIONAL"
        return "MODERN_FASHION"
    
    # Fallback
    if trad_score > modern_score:
        return "TRADITIONAL"
    elif modern_score > 0:
        return "MODERN_FASHION"
    
    return "GENERAL"


def find_suitable_stores(existing_stores: list, category: str, 
                         github_stores_by_id: dict, 
                         github_store_id: int = None) -> list:
    """
    Tìm Store phù hợp với loại sản phẩm.
    
    Ưu tiên #1: Nếu có inventory mapping từ Github (github_store_id), 
                dùng trực tiếp store đó (Context-Aware!).
    Ưu tiên #2: Nếu store đó chưa tồn tại trong DB, tạo mới từ data Github.
    Ưu tiên #3: Fallback sang store hiện có trong DB theo category.
    """
    # Nếu biết chính xác store_id từ inventory mapping → trả về luôn
    if github_store_id is not None:
        if github_store_id in github_stores_by_id:
            return [github_store_id]  # Sẽ được tạo/lookup khi insert
    
    # Fallback: tìm trong DB stores theo category
    allowed_cats = STORE_CATEGORY_MAP.get(category, STORE_CATEGORY_MAP["GENERAL"])
    matched = [s for s in existing_stores if s.category in allowed_cats]
    
    if not matched:
        # Mở rộng search nếu không tìm thấy
        matched = existing_stores
    
    return matched


# ═══════════════════════════════════════════════════════════════════════════
#  STEP 4: EXECUTE INSERT (DB COMMIT)
# ═══════════════════════════════════════════════════════════════════════════
def seed_data():
    """Main seeding logic."""
    
    print("=" * 72)
    print("  🌱 AEGIS O2O — CONTEXT-AWARE PRODUCT SEEDING")
    print("=" * 72)
    
    # ── 1. Fetch data from Github ────────────────────────────────────
    all_stores = []
    all_products = []
    all_inventories = []
    
    for label, url in DATA_FILES.items():
        try:
            sql_content = fetch_sql_from_github(url)
            stores, products, inventories = parse_sql_data(sql_content, label)
            all_stores.extend(stores)
            all_products.extend(products)
            all_inventories.extend(inventories)
        except Exception as e:
            print(f"   ❌ Lỗi tải {label}: {e}")
            return
    
    print(f"\n📊 TỔNG CỘNG: {len(all_stores)} stores, {len(all_products)} products, {len(all_inventories)} inventory")
    
    # ── 2. Build lookup maps ─────────────────────────────────────────
    github_stores_by_id = {s["store_id"]: s for s in all_stores}
    
    # Build inventory map: product_id -> [(store_id, stock), ...]
    inventory_map = {}
    for inv in all_inventories:
        pid = inv["product_id"]
        if pid not in inventory_map:
            inventory_map[pid] = []
        inventory_map[pid].append((inv["store_id"], inv["stock"], inv["inventory_id"]))
    
    # ── 3. Connect to DB ─────────────────────────────────────────────
    db = SessionLocal()
    
    try:
        # Load existing stores for fallback matching
        existing_db_stores = db.query(Store).all()
        print(f"\n🏬 Stores hiện có trong DB: {len(existing_db_stores)}")
        
        # Track which stores we've already ensured exist
        ensured_store_ids = set(s.store_id for s in existing_db_stores)
        
        # ── 4. Upsert Github Stores ─────────────────────────────────
        print(f"\n🏪 Đang nạp {len(all_stores)} stores từ Github...")
        stores_created = 0
        stores_skipped = 0
        
        for i, s_data in enumerate(all_stores):
            sid = s_data["store_id"]
            if sid in ensured_store_ids:
                stores_skipped += 1
                continue
            
            # Determine category for the store based on source
            if s_data["source"] == "dacsan":
                store_cat = "food"   # Đặc sản → food
            else:
                store_cat = "store"  # Quần áo → store
            
            # Build geom for PostGIS spatial queries
            geom = None
            if s_data["lat"] and s_data["lon"]:
                geom = WKTElement(
                    f"POINT({s_data['lon']} {s_data['lat']})", srid=4326
                )
            
            new_store = Store(
                store_id=sid,
                name=s_data["name"],
                address=s_data["address"],
                place_id=s_data["place_id"],
                lat=s_data["lat"],
                lon=s_data["lon"],
                geom=geom,
                category=store_cat,
                rating=round(random.uniform(3.5, 5.0), 1),
            )
            db.merge(new_store)  # merge = INSERT or UPDATE
            ensured_store_ids.add(sid)
            stores_created += 1
            
            if (stores_created) % BATCH_SIZE == 0:
                db.commit()
                print(f"   💾 Committed {stores_created} stores...")
        
        db.commit()
        print(f"   ✅ Stores: {stores_created} created, {stores_skipped} skipped (already exist)")
        
        # ── 5. PHASE 1: Insert ALL Products first ────────────────────
        print(f"\n📦 PHASE 1: Đang nạp {len(all_products)} sản phẩm...")
        products_inserted = 0
        products_skipped = 0
        inventory_inserted = 0
        
        # Category stats
        category_stats = {"TRADITIONAL": 0, "MODERN_FASHION": 0, "ACCESSORIES": 0, "GENERAL": 0}
        
        # Track which products we successfully insert (for inventory phase)
        inserted_product_ids = set()
        product_categories = {}  # pid -> category
        
        # ★ BULK load all existing product IDs (single query, no per-row overhead)
        existing_pids = set(
            row[0] for row in db.query(Product.product_id).all()
        )
        print(f"   📋 Existing product IDs in DB: {len(existing_pids)}")
        
        batch_items = []
        
        for i, p_data in enumerate(all_products):
            pid = p_data["product_id"]
            
            # Categorize (always, for both new and existing)
            category = categorize_product(p_data["name"], p_data["source"])
            product_categories[pid] = category
            
            # Already in DB? Track for inventory but skip insert
            if pid in existing_pids:
                products_skipped += 1
                inserted_product_ids.add(pid)  # Still track for inventory phase
                continue
            
            category_stats[category] = category_stats.get(category, 0) + 1
            
            # Determine tags
            tags_list = []
            if p_data["source"] == "dacsan":
                tags_list.append("đặc sản")
                tags_list.append("quà tặng")
            else:
                tags_list.append("thời trang")
            tags_list.append(category.lower().replace("_", " "))
            tags = ",".join(tags_list)
            
            # Queue product for insert
            # Map source → store category for strict matching
            product_cat = "food" if p_data["source"] == "dacsan" else "store"
            new_product = Product(
                product_id=pid,
                name=p_data["name"],
                description=p_data["description"],
                price=p_data["price"],
                original_price=int(p_data["price"] * 1.2) if p_data["price"] > 1000 else p_data["price"],
                image_url=p_data["image_url"],
                category=product_cat,
                tags=tags,
                created_at=datetime.now(timezone.utc),
            )
            db.add(new_product)
            inserted_product_ids.add(pid)
            existing_pids.add(pid)  # Prevent duplicates within this run
            products_inserted += 1
            
            if products_inserted <= 10:
                print(f"   [Product] {p_data['name'][:60]:60s} ({category})")
            
            # Batch commit products ONLY
            if products_inserted % BATCH_SIZE == 0:
                db.commit()
                print(f"   💾 Committed {products_inserted} products...")
        
        # Final product commit
        db.commit()
        print(f"   ✅ Products: {products_inserted} inserted, {products_skipped} skipped")
        
        # ── 6. PHASE 2: Insert Inventory with Context-Aware Mapping ──
        print(f"\n🔗 PHASE 2: Đang nạp inventory (Context-Aware Mapping)...")
        
        # ★ BULK load existing inventory IDs AND (store_id, product_id) pairs
        existing_inv_ids = set(
            row[0] for row in db.query(Inventory.inventory_id).all()
        )
        existing_store_product_pairs = set(
            (row[0], row[1]) for row in db.query(Inventory.store_id, Inventory.product_id).all()
        )
        print(f"   📋 Existing: {len(existing_inv_ids)} inventory IDs, {len(existing_store_product_pairs)} (store,product) pairs")
        
        # Build product name lookup for logging
        product_name_map = {p["product_id"]: p["name"] for p in all_products}
        
        for i, p_data in enumerate(all_products):
            pid = p_data["product_id"]
            
            # Only create inventory for products that exist in DB
            if pid not in inserted_product_ids:
                continue
            
            category = product_categories.get(pid, "GENERAL")
            
            # ── Context-Aware: Use mapping from SQL file (NOT random!) ──
            if pid in inventory_map:
                for store_id, stock, inv_id in inventory_map[pid]:
                    # Ensure the target store exists
                    if store_id not in ensured_store_ids:
                        continue
                    
                    # Skip if inventory_id OR (store_id, product_id) already exists
                    if inv_id in existing_inv_ids:
                        continue
                    if (store_id, pid) in existing_store_product_pairs:
                        continue
                    
                    new_inv = Inventory(
                        inventory_id=inv_id,
                        product_id=pid,
                        store_id=store_id,
                        stock=stock,
                    )
                    db.add(new_inv)
                    existing_inv_ids.add(inv_id)
                    existing_store_product_pairs.add((store_id, pid))
                    inventory_inserted += 1
                    
                    # Log first 20 + every 100th
                    if inventory_inserted <= 20 or inventory_inserted % 100 == 0:
                        store_name = github_stores_by_id.get(store_id, {}).get("name", f"Store#{store_id}")
                        print(f"   [Inventory] {p_data['name'][:45]:45s} → {store_name[:35]} ({category})")
            else:
                # Fallback: Assign to suitable store from DB by category
                suitable = find_suitable_stores(existing_db_stores, category, github_stores_by_id)
                if suitable and isinstance(suitable[0], Store):
                    chosen_store = random.choice(suitable[:10])
                    # Check if (store_id, product_id) pair already exists
                    if (chosen_store.store_id, pid) in existing_store_product_pairs:
                        continue
                    next_inv_id = max(existing_inv_ids) + 1 if existing_inv_ids else 200000
                    
                    new_inv = Inventory(
                        inventory_id=next_inv_id,
                        product_id=pid,
                        store_id=chosen_store.store_id,
                        stock=random.randint(10, 200),
                    )
                    db.add(new_inv)
                    existing_inv_ids.add(next_inv_id)
                    existing_store_product_pairs.add((chosen_store.store_id, pid))
                    inventory_inserted += 1
                    
                    if inventory_inserted <= 20 or inventory_inserted % 100 == 0:
                        print(f"   [Inventory] {p_data['name'][:45]:45s} → {chosen_store.name[:35]} ({category}) [fallback]")
            
            # Batch commit inventory
            if inventory_inserted > 0 and inventory_inserted % BATCH_SIZE == 0:
                db.commit()
                print(f"   💾 Committed {inventory_inserted} inventory records...")
        
        # Final inventory commit
        db.commit()
        print(f"   ✅ Inventory: {inventory_inserted} records created")
        
        # ── 6. Print Summary ─────────────────────────────────────────
        print("\n" + "=" * 72)
        print("  📊 SEEDING REPORT")
        print("=" * 72)
        print(f"  🏪 Stores Created:    {stores_created}")
        print(f"  🏪 Stores Skipped:    {stores_skipped}")
        print(f"  📦 Products Inserted: {products_inserted}")
        print(f"  📦 Products Skipped:  {products_skipped}")
        print(f"  🔗 Inventory Created: {inventory_inserted}")
        print(f"\n  📂 Phân loại sản phẩm:")
        for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            emoji = {"TRADITIONAL": "🏛️", "MODERN_FASHION": "👗", "ACCESSORIES": "👜", "GENERAL": "📦"}.get(cat, "📦")
            print(f"     {emoji} {cat:20s}: {count:5d} sản phẩm")
        
        # Verify totals
        total_products = db.query(Product).count()
        total_inventory = db.query(Inventory).count()
        total_stores = db.query(Store).count()
        print(f"\n  🗃️  TỔNG TRONG DB SAU SEEDING:")
        print(f"     Stores:    {total_stores}")
        print(f"     Products:  {total_products}")
        print(f"     Inventory: {total_inventory}")
        print("=" * 72)
        print("  ✅ SEEDING HOÀN TẤT!")
        print("=" * 72)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ LỖI SEEDING: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    seed_data()
