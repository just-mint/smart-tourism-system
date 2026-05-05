import os
import sys

# Thêm thư mục gốc vào sys.path để có thể import từ backend
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.core.ai_engine import analyze_input, generate_story

def run_tests():
    print("=== BẮT ĐẦU TEST AI ENGINE ===")
    
    # Test 1: Bóc tách từ khóa từ văn bản (Sử dụng Groq)
    print("\n[Test 1] Phân tích văn bản:")
    text_input = "Tôi muốn mua một chiếc nón lá và áo dài truyền thống để làm quà"
    print(f"Input: {text_input}")
    keywords = analyze_input(user_input=text_input)
    print(f"Output Keywords: {keywords}")
    
    # Test 2: Tạo câu chuyện văn hóa (Sử dụng Groq)
    print("\n[Test 2] Tạo câu chuyện văn hóa:")
    item = "Nón lá"
    desc = "Nón lá là biểu tượng truyền thống của người phụ nữ Việt Nam, che nắng che mưa."
    story = generate_story(item, desc)
    print(f"Output Story:\n{story}")
    
    # Test 3: Nhận diện ảnh bằng Groq Vision (DÙNG ẢNH LOCAL)
    print("\n[Test 3] Nhận diện ảnh bằng Groq Vision (Local Image):")
    
    image_path = "sample_test_image.jpg.png"  # 👉 bạn tự bỏ ảnh vào cùng thư mục với file này
    
    if not os.path.exists(image_path):
        print(f"[!] Không tìm thấy ảnh: {image_path}")
        print("👉 Hãy thêm file test.jpg vào thư mục project")
        return
    
    print(f"Input Image Path: {image_path}")
    image_keywords = analyze_input(image_path=image_path)
    print(f"Output Image Keywords: {image_keywords}")

if __name__ == "__main__":
    run_tests()