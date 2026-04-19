import asyncio
import streamlit as st

from backend.core.ai_engine import analyze_input, generate_story
from backend.core.shop_filter import filter_shops_by_keywords, convert_shops_for_member_e
from backend.database.db_manager import init_db, get_wishlist, add_to_wishlist
from backend.core.ranking_algo import RankingAlgorithm
from backend.core.tsp_solver import TSPSolver
import frontend.ui as ui

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAGE_TITLE = "Smart Tourism System"
USER_LAT = 10.762622
USER_LON = 106.660172
TOP_N_SMART = 3

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

def setup():
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    init_db()
    _init_session_state()


def _init_session_state():
    defaults = {
        "search_results": [],
        "selected_shops": [],
        "final_route": None,
        "mode": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ---------------------------------------------------------------------------
# TSP
# ---------------------------------------------------------------------------

async def _run_tsp(shops: list) -> dict | None:
    if not shops:
        return None
    user_coord = (USER_LON, USER_LAT)
    shop_coords = [(s["lon"], s["lat"]) for s in shops]
    return await TSPSolver.run_tsp_pipeline(user_coord, shop_coords)


def compute_route(shops: list) -> dict | None:
    return asyncio.run(_run_tsp(shops))

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def handle_search(user_text: str, uploaded_file) -> None:
    """Runs AI keyword extraction and filters shops; stores results in session."""
    keywords = analyze_input(user_input=user_text or None, image_path=uploaded_file)
    if not keywords:
        st.error("⚠️ Không tìm thấy từ khóa phù hợp. Vui lòng thử lại!")
        return
    st.session_state.search_results = filter_shops_by_keywords(keywords)

# ---------------------------------------------------------------------------
# Route Modes
# ---------------------------------------------------------------------------

def run_smart_magic() -> None:
    """Rank top N shops and compute optimal route automatically."""
    if not st.session_state.search_results:
        st.warning("Vui lòng nhập nhu cầu trước!")
        return

    shops_for_ranking = convert_shops_for_member_e(
        st.session_state.search_results, USER_LAT, USER_LON
    )
    top_shops = RankingAlgorithm.rank_items(shops_for_ranking)[:TOP_N_SMART]
    st.session_state.final_route = compute_route(top_shops)
    st.session_state.mode = "smart"


def run_customize(selected_shops: list) -> None:
    """Compute route from user-selected shops."""
    shops_for_e = convert_shops_for_member_e(selected_shops, USER_LAT, USER_LON)
    st.session_state.final_route = compute_route(shops_for_e)
    st.session_state.mode = "customize"


def run_wishlist() -> None:
    """Load wishlist shops and compute route."""
    wish_shops = get_wishlist()
    if not wish_shops:
        st.info("Wishlist của bạn đang trống.")
        return
    shops_for_e = convert_shops_for_member_e(wish_shops, USER_LAT, USER_LON)
    st.session_state.final_route = compute_route(shops_for_e)
    st.session_state.mode = "wishlist"

# ---------------------------------------------------------------------------
# UI Sections
# ---------------------------------------------------------------------------

def render_input_section() -> tuple[str, object]:
    """Renders the search bar and file uploader; returns (user_text, uploaded_file)."""
    col_input, col_action = st.columns([2, 1])

    with col_input:
        user_text = st.text_input(
            "Bạn muốn tìm gì?",
            placeholder="Ví dụ: nón lá, áo sơ mi...",
        )
        uploaded_file = st.file_uploader(
            "Hoặc chụp ảnh món đồ", type=["jpg", "png", "jpeg"]
        )

    with col_action:
        st.write("### Chọn chế độ")
        btn_smart = st.button("✨ Smart Magic (Nhanh)")
        btn_wishlist = st.button("❤️ Mở Wishlist")

    return user_text, uploaded_file, btn_smart, btn_wishlist


def render_search_results() -> None:
    """Shows search result cards with checkboxes; triggers Customize route."""
    st.write("### 🔍 Kết quả tìm kiếm (Tích chọn để đi - Customize)")
    selected = ui.render_shop_cards(st.session_state.search_results)

    if selected and st.button("🚀 Bắt đầu lộ trình đã chọn"):
        run_customize(selected)


def render_route_output() -> None:
    """Displays the final map, cultural story, and a reset button."""
    ui.display_map(st.session_state.final_route)

    st.write("---")
    st.header("📜 Góc Văn Hóa")

    # Index 0 = user origin; index 1 = first shop in optimised path
    first_shop_id = st.session_state.final_route["opt_path_indexes"][1]
    story = generate_story("Món đồ bạn tìm", "Dữ liệu văn hóa từ shop...")
    st.info(story)

    if st.button("🔄 Làm mới"):
        st.session_state.final_route = None
        st.session_state.mode = None
        st.rerun()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    setup()
    st.title("🚀 Hệ Thống Du Lịch Thông Minh")

    user_text, uploaded_file, btn_smart, btn_wishlist = render_input_section()

    # Trigger search whenever there is any input
    if user_text or uploaded_file:
        handle_search(user_text, uploaded_file)

    # Route mode buttons
    if btn_smart:
        run_smart_magic()
    if btn_wishlist:
        run_wishlist()

    # Show search results only when no route has been computed yet
    if st.session_state.search_results and not st.session_state.final_route:
        render_search_results()

    # Show final route output
    if st.session_state.final_route:
        render_route_output()


if __name__ == "__main__":
    main()