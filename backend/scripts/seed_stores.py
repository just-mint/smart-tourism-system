import random
import uuid
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2.elements import WKTElement

from app.core.config import settings
from app.domains.culture.model import Place
from app.domains.inventory.model import Store, Product, Inventory

def main():
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    places = db.query(Place).all()
    if not places:
        print("No places found. Ensure places are seeded first.")
        return

    print(f"Found {len(places)} places total.")
    places = random.sample(places, min(500, len(places)))
    print(f"Seeding stores around {len(places)} selected places...")

    # Seed 10 products
    products = db.query(Product).all()
    if not products:
        print("Creating mock products...")
        product_names = [
            "Nón Lá Sen Nghệ Thuật", "Lụa Tơ Tằm Bảo Lộc", "Gốm Sứ Bát Tràng Men", 
            "Cafe Chồn Đặc Sản", "Trà Cung Đình Huế", "Túi Thổ Cẩm Sapa",
            "Móc Khóa Lưu Niệm", "Áo Thun Cờ Đỏ Sao Vàng", "Tranh Thêu Tay Mộc",
            "Đặc Sản Bánh Kẹo Local"
        ]
        for name in product_names:
            p = Product(
                name=name,
                price=random.randint(5, 50) * 10000,
                image_url="https://images.unsplash.com/photo-1548625361-ecac45bc1164?auto=format&fit=crop&w=500",
                description="Mock product for O2O shopping"
            )
            db.add(p)
        db.commit()
        products = db.query(Product).all()

    store_names = [
        "O2O Hub", "Local Market", "Souvenir Shop", "Craft Store", "Heritage Gifts"
    ]

    total_stores = 0
    for place in places:
        if not place.lat or not place.lon:
            continue
        
        # Check if already has stores around this place
        existing = db.query(Store).filter(Store.place_id == str(place.id)).count()
        if existing > 0:
            continue

        num_stores = random.randint(3, 6)
        for i in range(num_stores):
            lat_offset = random.uniform(-0.005, 0.005)
            lon_offset = random.uniform(-0.005, 0.005)
            slat = float(place.lat) + lat_offset
            slon = float(place.lon) + lon_offset

            geom = WKTElement(f"POINT({slon} {slat})", srid=4326)

            store = Store(
                place_id=str(uuid.uuid4())[:50],
                name=f"{place.name} - {random.choice(store_names)} {i+1}",
                category="shopping",
                address=f"Gần {place.name}",
                lat=slat,
                lon=slon,
                geom=geom,
                phone="0123456789",
                rating=round(random.uniform(3.5, 5.0), 1)
            )
            db.add(store)
            db.flush() # to get store.store_id
            
            # Add inventory
            for p in random.sample(products, random.randint(2, 5)):
                inv = Inventory(
                    store_id=store.store_id,
                    product_id=p.product_id,
                    stock=random.randint(10, 100)
                )
                db.add(inv)
            total_stores += 1

    db.commit()
    print(f"Successfully added {total_stores} new mock stores with inventory.")

if __name__ == "__main__":
    main()
