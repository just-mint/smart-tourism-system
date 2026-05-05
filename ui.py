import streamlit as st

def render_shop_cards(search_results):
    """Hiển thị danh sách cửa hàng và checkbox để người dùng chọn."""
    selected_shops = []
    if not search_results:
        st.info("Không có cửa hàng nào phù hợp.")
        return selected_shops
        
    for idx, shop in enumerate(search_results):
        name = shop.get("name", f"Cửa hàng {idx + 1}")
        desc = shop.get("description", "Không có mô tả")
        
        # Nếu người dùng tick chọn checkbox, thêm shop này vào danh sách selected
        if st.checkbox(f"📍 {name} - {desc}", key=f"shop_{idx}"):
            selected_shops.append(shop)
            
    return selected_shops

def display_map(final_route):
    """Hiển thị bản đồ lộ trình (hiện đang hiển thị data thô dưới dạng JSON để test)."""
    st.write("### 🗺️ Bản đồ Lộ Trình")
    st.json(final_route)