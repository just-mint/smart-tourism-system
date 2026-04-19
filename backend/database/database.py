import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "wishlist.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            shop_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            category TEXT,
            price INTEGER,
            rating REAL,
            lat REAL,
            lng REAL,
            description_raw TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_to_wishlist(shop):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO wishlist (
            shop_id, name, address, category, price, rating, lat, lng, description_raw
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        shop["id"],
        shop["name"],
        shop["address"],
        shop["category"],
        shop["price"],
        shop["rating"],
        shop["coords"]["lat"],
        shop["coords"]["lng"],
        shop["description_raw"]
    ))

    conn.commit()
    conn.close()

    return f"Đã lưu {shop['name']} vào wishlist."


def get_wishlist():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT shop_id, name, address, category, price, rating, lat, lng, description_raw
        FROM wishlist
        ORDER BY name
    """)

    rows = cursor.fetchall()
    conn.close()

    wishlist = []

    for row in rows:
        wishlist.append({
            "id": row[0],
            "name": row[1],
            "address": row[2],
            "category": row[3],
            "price": row[4],
            "rating": row[5],
            "coords": {
                "lat": row[6],
                "lng": row[7]
            },
            "description_raw": row[8]
        })

    return wishlist


def remove_from_wishlist(shop_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM wishlist WHERE shop_id = ?", (shop_id,))
    deleted_rows = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted_rows > 0:
        return f"Đã xoá shop {shop_id} khỏi wishlist."
    return f"Không tìm thấy shop {shop_id} trong wishlist."