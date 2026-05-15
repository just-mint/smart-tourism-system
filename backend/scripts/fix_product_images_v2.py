"""
fix_product_images_v2.py
Cập nhật image_url của sản phẩm dựa trên keyword trong TÊN sản phẩm,
không phải category của store.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aegis_user:aegis_secret@localhost:5432/travel_app"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ——— Bảng mapping keyword → Unsplash URL ———————————————————————————————
KEYWORD_IMAGE_MAP = [
    # Quần áo / thời trang
    ("áo dài",      "https://images.unsplash.com/photo-1549416568-154673de01f7?auto=format&fit=crop&w=700&q=80"),
    ("áo khoác",    "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=700&q=80"),
    ("áo thun",     "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=700&q=80"),
    ("áo",          "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=700&q=80"),
    ("quần",        "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=700&q=80"),
    ("váy",         "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?auto=format&fit=crop&w=700&q=80"),
    ("khăn",        "https://images.unsplash.com/photo-1618698282361-b0e6ab7bc5bc?auto=format&fit=crop&w=700&q=80"),

    # Giày dép / phụ kiện
    ("giày sneaker","https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80"),
    ("sneaker",     "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80"),
    ("giày",        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80"),
    ("dép",         "https://images.unsplash.com/photo-1603487742131-4160ec999306?auto=format&fit=crop&w=700&q=80"),
    ("balo",        "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=700&q=80"),
    ("túi xách",    "https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?auto=format&fit=crop&w=700&q=80"),
    ("túi",         "https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?auto=format&fit=crop&w=700&q=80"),
    ("kính",        "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=700&q=80"),
    ("mũ",          "https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&w=700&q=80"),
    ("nón lá",      "https://images.unsplash.com/photo-1628116518175-103362aab35b?auto=format&fit=crop&w=700&q=80"),
    ("nón",         "https://images.unsplash.com/photo-1628116518175-103362aab35b?auto=format&fit=crop&w=700&q=80"),
    ("vòng",        "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?auto=format&fit=crop&w=700&q=80"),
    ("đồng hồ",     "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=700&q=80"),

    # Nước hoa / mỹ phẩm
    ("nước hoa",    "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=700&q=80"),
    ("mỹ phẩm",     "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=700&q=80"),
    ("son",         "https://images.unsplash.com/photo-1586495777744-4e6b1a8a0c6b?auto=format&fit=crop&w=700&q=80"),
    ("kem",         "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=700&q=80"),

    # Đồ ăn / cà phê
    ("cà phê",      "https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=700&q=80"),
    ("cafe",        "https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=700&q=80"),
    ("trà",         "https://images.unsplash.com/photo-1576092762791-dd9e2220abd4?auto=format&fit=crop&w=700&q=80"),
    ("bánh mì",     "https://images.unsplash.com/photo-1606850239561-ebbc6f23b2c2?auto=format&fit=crop&w=700&q=80"),
    ("bánh",        "https://images.unsplash.com/photo-1555507036-ab1e4006aa0a?auto=format&fit=crop&w=700&q=80"),
    ("nước mắm",    "https://images.unsplash.com/photo-1627042633145-b780d842ba45?auto=format&fit=crop&w=700&q=80"),
    ("hạt điều",    "https://images.unsplash.com/photo-1613941426466-993d0de3e157?auto=format&fit=crop&w=700&q=80"),
    ("mứt",         "https://images.unsplash.com/photo-1622312695574-8b63486ab9dc?auto=format&fit=crop&w=700&q=80"),

    # Đồ lưu niệm / thủ công mỹ nghệ
    ("đèn lồng",    "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=700&q=80"),
    ("xích lô",     "https://images.unsplash.com/photo-1588691517409-7681e8f96ce7?auto=format&fit=crop&w=700&q=80"),
    ("gốm",         "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=700&q=80"),
    ("tranh",       "https://images.unsplash.com/photo-1578301978693-85fa9c026f43?auto=format&fit=crop&w=700&q=80"),
    ("tượng",       "https://images.unsplash.com/photo-1552554746-817887372d6d?auto=format&fit=crop&w=700&q=80"),
    ("chuông",      "https://images.unsplash.com/photo-1534954703772-2d8c36b85d34?auto=format&fit=crop&w=700&q=80"),
    ("lụa",         "https://images.unsplash.com/photo-1549416568-154673de01f7?auto=format&fit=crop&w=700&q=80"),
]

GENERIC_FALLBACK = "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=700&q=80"


def pick_image(name: str) -> str:
    name_lower = (name or "").lower()
    for keyword, url in KEYWORD_IMAGE_MAP:
        if keyword in name_lower:
            return url
    return GENERIC_FALLBACK


def run():
    db = SessionLocal()
    print("Bắt đầu fix image_url theo tên sản phẩm...")

    rows = db.execute(text("SELECT product_id, name FROM products")).fetchall()
    count = 0
    for pid, name in rows:
        img = pick_image(name)
        db.execute(
            text("UPDATE products SET image_url = :img WHERE product_id = :pid"),
            {"img": img, "pid": pid},
        )
        count += 1
        if count % 200 == 0:
            db.commit()
            print(f"  Đã xử lý {count}/{len(rows)}...")

    db.commit()
    db.close()
    print(f"✅ Hoàn tất! Đã cập nhật image_url cho {count} sản phẩm.")


if __name__ == "__main__":
    run()
