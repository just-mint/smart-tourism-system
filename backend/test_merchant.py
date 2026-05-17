import os
import requests
import random
import string
from time import sleep

API_URL = "http://localhost:8000/api/v1"

def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def run_test():
    print("🚀 BẮT ĐẦU KIỂM THỬ LUỒNG MERCHANT / O2O CATALOG")
    
    # 1. Admin Login
    print("\n[1] Admin Login...")
    r = requests.post(
        f"{API_URL}/login/access-token", 
        data={"username": "admin@example.com", "password": "changethis"}
    )
    r.raise_for_status()
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✅ Đăng nhập Admin thành công.")

    # 2. Tạo User & Cấp quyền Merchant
    print("\n[2] Setup Merchant User...")
    merchant_email = f"merchant_{random_string()}@example.com"
    r = requests.post(
        f"{API_URL}/users/", 
        json={"email": merchant_email, "password": "password123", "full_name": "Nguyen Gian Hang"},
        headers=admin_headers
    )
    r.raise_for_status()
    merchant_id = r.json()["id"]
    
    r = requests.patch(
        f"{API_URL}/inventory/admin/users/{merchant_id}/merchant?is_merchant=true",
        headers=admin_headers
    )
    r.raise_for_status()
    print(f"✅ Tạo Merchant thành công: {merchant_email}")

    # 3. Merchant Login
    print("\n[3] Merchant Login...")
    r = requests.post(
        f"{API_URL}/login/access-token", 
        data={"username": merchant_email, "password": "password123"}
    )
    r.raise_for_status()
    merchant_token = r.json()["access_token"]
    merchant_headers = {"Authorization": f"Bearer {merchant_token}"}
    print("✅ Đăng nhập Merchant thành công.")

    # Lấy danh mục "Ẩm thực & Đặc sản"
    r = requests.get(f"{API_URL}/inventory/categories")
    categories = r.json()
    food_cat = next((c for c in categories if c["slug"] == "am-thuc-dac-san"), categories[0])

    # 4. Create Store
    print("\n[4] Create Store...")
    store_data = {
        "name": "Cà Phê Muối Chú Long",
        "category": "Cafe / Trà sữa",
        "address": "123 Đường Điện Biên Phủ, Quận 1",
        "lat": 10.785,
        "lon": 106.698,
        "phone": "0987654321",
        "opening_hours": {"mon": {"open": "07:00", "close": "22:00"}},
        "service_radius": 3000
    }
    r = requests.post(f"{API_URL}/inventory/stores", json=store_data, headers=merchant_headers)
    r.raise_for_status()
    store_id = r.json()["store_id"]
    print(f"✅ Tạo Store thành công (ID: {store_id}).")

    # 5. Create Product
    print("\n[5] Create Product...")
    product_data = {
        "name": "Cà Phê Muối Đặc Biệt",
        "description": "Thức uống siêu hot hit của giới trẻ",
        "sku": f"CFM-{random_string(4)}".upper(),
        "price": 30000, # 30k
        "category_id": food_cat["id"]
    }
    r = requests.post(f"{API_URL}/inventory/products", json=product_data, headers=merchant_headers)
    r.raise_for_status()
    product_id = r.json()["product_id"]
    print(f"✅ Tạo Product thành công (ID: {product_id}, Giá chuẩn: 30000).")

    # 6. Upsert Inventory (Custom store_price)
    print("\n[6] Đưa sản phẩm vào kho & cấu hình store_price...")
    inv_data = {
        "product_id": product_id,
        "stock": 50,
        "store_price": 25000, # Khuyến mãi còn 25k tại store này
        "is_available": True
    }
    r = requests.put(f"{API_URL}/inventory/stores/{store_id}/inventory", json=inv_data, headers=merchant_headers)
    r.raise_for_status()
    print("✅ Đưa vào kho thành công (Tồn kho: 50, Giá tại cửa hàng: 25000).")

    # 7. Faceted Search
    print("\n[7] Khách hàng tìm kiếm Faceted Search...")
    search_params = {
        "q": "Cà phê",
        "max_price": 28000, # Khách chỉ mua dưới 28k
        "lat": 10.780,
        "lon": 106.690,
        "radius": 5000, # Trong vòng 5km
        "in_stock_only": True
    }
    r = requests.get(f"{API_URL}/inventory/search", params=search_params)
    r.raise_for_status()
    search_res = r.json()
    
    print(f"➡️  Tổng số sản phẩm khớp: {search_res['total_products']}")
    
    passed = False
    for p in search_res["products"]:
        if p["product_id"] == product_id:
            passed = True
            print(f"🎉 TÌM THẤY SẢN PHẨM: {p['name']} - Giá: {p['price']}đ - Khoảng cách: {p['distance_m']}m - Cửa hàng: {p['store_name']}")
    
    if passed:
        print("\n🏆 KẾT LUẬN: Nghiệm thu tính năng thành công 100%. Luồng dữ liệu chạy mượt mà.")
    else:
        print("\n❌ LỖI: Không tìm thấy sản phẩm trong kết quả search. Cần kiểm tra lại logic.")

if __name__ == "__main__":
    run_test()
