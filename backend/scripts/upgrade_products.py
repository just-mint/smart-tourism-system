import logging
import os
import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_secret@localhost:5432/travel_app")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
logger = logging.getLogger(__name__)

O2O_PRODUCTS = [
    {"name": "Áo dài lụa tơ tằm truyền thống", "price": 1200000, "img": "https://images.unsplash.com/photo-1549416568-154673de01f7?auto=format&fit=crop&w=500"},
    {"name": "Nón lá sen thêu tay nghệ thuật", "price": 350000, "img": "https://images.unsplash.com/photo-1628116518175-103362aab35b?auto=format&fit=crop&w=500"},
    {"name": "Cà phê chồn Tây Nguyên nguyên chất", "price": 850000, "img": "https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=500"},
    {"name": "Trà sen Tây Hồ cao cấp", "price": 450000, "img": "https://images.unsplash.com/photo-1576092762791-dd9e2220abd4?auto=format&fit=crop&w=500"},
    {"name": "Mô hình xích lô đồng mini", "price": 250000, "img": "https://images.unsplash.com/photo-1588691517409-7681e8f96ce7?auto=format&fit=crop&w=500"},
    {"name": "Đèn lồng Hội An lụa dệt", "price": 150000, "img": "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=500"},
    {"name": "Tranh gạo thư pháp", "price": 600000, "img": "https://images.unsplash.com/photo-1578301978693-85fa9c026f43?auto=format&fit=crop&w=500"},
    {"name": "Khăn rằn Nam Bộ dệt thủ công", "price": 80000, "img": "https://images.unsplash.com/photo-1618698282361-b0e6ab7bc5bc?auto=format&fit=crop&w=500"},
    {"name": "Bộ gốm Bát Tràng men rạn", "price": 1500000, "img": "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=500"},
    {"name": "Nước mắm nhỉ Phú Quốc 40 độ đạm", "price": 120000, "img": "https://images.unsplash.com/photo-1627042633145-b780d842ba45?auto=format&fit=crop&w=500"},
    {"name": "Đông hồ tranh dân gian Đám cưới chuột", "price": 300000, "img": "https://images.unsplash.com/photo-1563806935473-b3c078028ddc?auto=format&fit=crop&w=500"},
    {"name": "Mứt sen trần", "price": 150000, "img": "https://images.unsplash.com/photo-1622312695574-8b63486ab9dc?auto=format&fit=crop&w=500"},
    {"name": "Hạt điều rang muối Bình Phước", "price": 220000, "img": "https://images.unsplash.com/photo-1613941426466-993d0de3e157?auto=format&fit=crop&w=500"},
    {"name": "Túi xách mây tre đan", "price": 450000, "img": "https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?auto=format&fit=crop&w=500"},
    {"name": "Chuông gió đồng gốm", "price": 180000, "img": "https://images.unsplash.com/photo-1534954703772-2d8c36b85d34?auto=format&fit=crop&w=500"},
    {"name": "Tượng gỗ mỹ nghệ Di Lặc", "price": 3500000, "img": "https://images.unsplash.com/photo-1552554746-817887372d6d?auto=format&fit=crop&w=500"}
]

def run():
    db = SessionLocal()
    logger.info("Bắt đầu cập nhật sản phẩm...")
    products = db.execute(text("SELECT product_id FROM products")).fetchall()

    count = 0
    for p in products:
        pid = p[0]
        item = random.choice(O2O_PRODUCTS)

        # Vary price slightly to look natural
        variance = random.uniform(0.9, 1.1)
        final_price = int(item["price"] * variance)
        original_price = int(final_price * random.uniform(1.1, 1.3))

        desc = f"Tuyệt tác {item['name'].lower()} mang đậm phong cách văn hóa du lịch địa phương. Chất lượng hoàn hảo cho khách mua sắm O2O."

        db.execute(
            text("""
                UPDATE products
                SET name = :name,
                    price = :price,
                    original_price = :original_price,
                    description = :desc,
                    image_url = :image_url
                WHERE product_id = :pid
            """),
            {
                "name": item["name"],
                "price": final_price,
                "original_price": original_price,
                "desc": desc,
                "image_url": item["img"],
                "pid": pid
            }
        )
        count += 1
        if count % 100 == 0:
            db.commit()
            logger.info("Đã cập nhật %s sản phẩm", count)

    db.commit()
    db.close()
    logger.info("Đã hoàn tất cập nhật dữ liệu sản phẩm chuẩn O2O!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
