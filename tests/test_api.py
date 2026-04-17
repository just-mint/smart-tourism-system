import os
import sys
import time
from dotenv import load_dotenv

# 1. Định nghĩa đường dẫn gốc (Root Directory)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Load biến môi trường từ file .env ở thư mục gốc
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 3. Import các hàm từ module ai_engine của bạn
# Đảm bảo file modules/ai_engine.py đã đổi tên model sang gemini-3.1-flash-lite-preview
from modules.ai_engine import analyze_input, generate_story

def main():
    print("="*50)
    print("   HỆ THỐNG PHÂN TÍCH ĐA PHƯƠNG THỨC (GEMINI 3.1 LITE)")
    print("="*50)
    
    all_keywords = []

    # --- PHẦN 1: XỬ LÝ VĂN BẢN ---
    user_input = "Tôi muốn mua một chiếc nón lá và một cái áo sơ mi"
    print(f"\n[TEXT] Đang xử lý yêu cầu: '{user_input}'")
    try:
        text_results = analyze_input(user_input=user_input)
        all_keywords.extend(text_results)
        print(f"-> Từ khóa bóc tách: {text_results}")
    except Exception as e:
        print(f"[!] Lỗi khi xử lý văn bản: {e}")

    # --- PHẦN 2: XỬ LÝ HÌNH ẢNH ---
    # Tìm file ảnh tại thư mục gốc
    image_file_name = "ao_so_mi.jpg" 
    image_path = os.path.join(BASE_DIR, image_file_name)
    
    if os.path.exists(image_path):
        print(f"\n[IMAGE] Đang nhận diện hình ảnh: {image_file_name}...")
        try:
            img_results = analyze_input(image_path=image_path)
            all_keywords.extend(img_results)
            print(f"-> Từ khóa từ ảnh: {img_results}")
        except Exception as e:
            print(f"[!] Lỗi khi xử lý hình ảnh: {e}")
    else:
        print(f"\n[!] Cảnh báo: Không tìm thấy file '{image_path}'.")
        print("Hãy đảm bảo bạn đã để file ảnh trong thư mục gốc dự án.")

    # --- PHẦN 3: TỔNG HỢP VÀ TẠO STORY ---
    # Làm sạch từ khóa (xóa khoảng trắng, chuyển chữ thường, lọc trùng)
    unique_keywords = list(set([k.lower().strip() for k in all_keywords if k]))
    
    if not unique_keywords:
        print("\n[!] Không tìm thấy sản phẩm nào để xử lý tiếp.")
        return

    print("\n" + "="*30)
    print(f"BẮT ĐẦU SÁNG TẠO NỘI DUNG ({len(unique_keywords)} món đồ)")
    print("="*30)

    for item in unique_keywords:
        # Giả lập dữ liệu thô (sau này sẽ lấy từ data.json của Thành viên A)
        if "nón lá" in item:
            raw_info = "Làm thủ công từ lá cọ phơi khô, vùng nón Chuông, biểu tượng văn hóa Việt."
        elif "áo sơ mi" in item or "shirt" in item or "áo" in item:
            raw_info = "Chất liệu cotton thoáng mát, đường may tinh tế, phù hợp công sở."
        else:
            raw_info = "Sản phẩm chất lượng cao, mang lại sự tiện dụng cho khách du lịch."

        print(f"\n[*] Đang viết story cho: {item.upper()}")
        try:
            # Dùng Gemini để viết truyện
            story = generate_story(item, raw_info)
            print(f"Cảm hứng: {story}")
            # Nghỉ 1 chút để tránh bị khóa API (Rate Limit)
            time.sleep(1)
        except Exception as e:
            print(f"-> [!] Lỗi tạo story cho {item}: {e}")

    print("\n" + "="*50)
    print("              HOÀN THÀNH NHIỆM VỤ TEST")
    print("="*50)

if __name__ == "__main__":
    main()