import os
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_secret@localhost:5432/travel_app")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

IMG_COFFEE_FOOD = [
    {"name": "Cà phê Sữa Đá đập", "img": "https://images.unsplash.com/photo-1559525839-b184a4d698c7?auto=format&fit=crop&w=500", "desc": "Thức uống đặc trưng mang đậm hương vị Việt."},
    {"name": "Trà Sen Tây Hồ", "img": "https://images.unsplash.com/photo-1576092762791-dd9e2220abd4?auto=format&fit=crop&w=500", "desc": "Trà sen cao cấp thanh tao, giải nhiệt."},
    {"name": "Bánh Mì Pate Truyền Thống", "img": "https://images.unsplash.com/photo-1606850239561-ebbc6f23b2c2?auto=format&fit=crop&w=500", "desc": "Món ăn đường phố hấp dẫn không thể bỏ lỡ."},
    {"name": "Bánh ngọt Croissant", "img": "https://images.unsplash.com/photo-1555507036-ab1e4006aa0a?auto=format&fit=crop&w=500", "desc": "Bánh ngọt chuẩn vị Pháp, nướng giòn rụm."}
]

IMG_FASHION = [
    {"name": "Áo dài lụa tơ tằm", "img": "https://images.unsplash.com/photo-1549416568-154673de01f7?auto=format&fit=crop&w=500", "desc": "Trang phục truyền thống thanh lịch, sang trọng."},
    {"name": "Áo khoác Vintage", "img": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=500", "desc": "Hàng nhập khẩu cao cấp, phong cách cá tính."},
    {"name": "Khăn rằn Nam Bộ dệt thủ công", "img": "https://images.unsplash.com/photo-1618698282361-b0e6ab7bc5bc?auto=format&fit=crop&w=500", "desc": "Phụ kiện thời trang mang đậm chất dân dã."},
    {"name": "Túi xách mây tre đan", "img": "https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?auto=format&fit=crop&w=500", "desc": "Thiết kế thời trang từ chất liệu thân thiện môi trường."}
]

IMG_SOUVENIR = [
    {"name": "Nón lá sen thêu tay", "img": "https://images.unsplash.com/photo-1628116518175-103362aab35b?auto=format&fit=crop&w=500", "desc": "Quà lưu niệm ý nghĩa đậm nét văn hóa."},
    {"name": "Mô hình xích lô đồng mini", "img": "https://images.unsplash.com/photo-1588691517409-7681e8f96ce7?auto=format&fit=crop&w=500", "desc": "Đồ thủ công mỹ nghệ tinh xảo làm quà tặng."},
    {"name": "Đèn lồng Hội An lụa dệt", "img": "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=500", "desc": "Mang vẻ đẹp ánh sáng lung linh của phố cổ."},
    {"name": "Bộ gốm Bát Tràng men rạn", "img": "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=500", "desc": "Tuyệt tác gốm sứ nghệ thuật từ làng nghề truyền thống."}
]

IMG_DEFAULT = [
    {"name": "Gói Quà Tặng Đặc Biệt", "img": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=500", "desc": "Sản phẩm chất lượng cao đáng để trải nghiệm."},
    {"name": "Combo Tiện Ích Du Lịch", "img": "https://images.unsplash.com/photo-1492724441997-5dc865305da7?auto=format&fit=crop&w=500", "desc": "Trang bị thiết yếu cho chuyến đi của bạn."}
]

def run():
    db = SessionLocal()
    print("Bắt đầu chuẩn hóa hình ảnh sản phẩm theo Category...")
    
    # Lấy danh sách sản phẩm cùng với category của store
    query = text("""
        SELECT p.product_id, s.category
        FROM products p
        JOIN inventory i ON p.product_id = i.product_id
        JOIN stores s ON i.store_id = s.store_id
    """)
    products_with_category = db.execute(query).fetchall()
    
    count = 0
    # Dùng set để track các product_id đã update (vì 1 product có thể nằm ở nhiều store, update 1 lần là đủ)
    updated_pids = set()
    
    for row in products_with_category:
        pid, cat = row[0], row[1]
        
        if pid in updated_pids:
            continue
            
        cat_lower = str(cat).lower() if cat else ""
        
        # Mapping logic
        if any(x in cat_lower for x in ["cafe", "coffee", "restaurant", "food", "tea", "ăn", "uống", "nhà hàng", "trà", "cà phê"]):
            source = IMG_COFFEE_FOOD
        elif any(x in cat_lower for x in ["fashion", "clothing", "thời trang", "quần áo", "mặc", "boutique", "shop"]):
            source = IMG_FASHION
        elif any(x in cat_lower for x in ["souvenir", "gift", "lưu niệm", "quà", "thủ công", "craft"]):
            source = IMG_SOUVENIR
        else:
            source = IMG_DEFAULT
            
        item = random.choice(source)
        
        db.execute(
            text("""
                UPDATE products 
                SET name = :name,
                    description = :desc, 
                    image_url = :image_url
                WHERE product_id = :pid
            """),
            {
                "name": item["name"],
                "desc": item["desc"],
                "image_url": item["img"],
                "pid": pid
            }
        )
        updated_pids.add(pid)
        count += 1
        
        if count % 100 == 0:
            db.commit()
            print(f"Đã chuẩn hóa {count} sản phẩm...")
            
    db.commit()
    db.close()
    print(f"Đã hoàn tất chuẩn hóa {count} sản phẩm O2O theo Category!")

if __name__ == "__main__":
    run()
