import os
import ast
import re
import time
from groq import Groq
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image  

load_dotenv()

# Khởi tạo Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Khởi tạo model Gemini 
gemini_model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# Các model sử dụng
GROQ_MODEL = "llama-3.3-70b-versatile"

def analyze_input(user_input=None, image_path=None):
    keywords = []
    
    # 1. Nhận diện từ Hình ảnh (Sử dụng Gemini)
    if image_path:
        print(f"--- Đang phân tích ảnh bằng Gemini: {os.path.basename(image_path)} ---")
        try:
            img = Image.open(image_path)
            # Prompt yêu cầu Gemini trả về danh từ tiếng Việt trực tiếp
            prompt_vision = "Hãy nhìn vào ảnh này và liệt kê tên các món đồ vật chính có trong ảnh. Trả về kết quả dưới dạng danh sách các từ khóa, ngăn cách bằng dấu phẩy. Ví dụ: 'ao so mi, quan jean'"
            
            response = gemini_model.generate_content([prompt_vision, img])
            
            if response.text:
                # Tách từ khóa từ chuỗi trả về
                img_keywords = [k.strip() for k in response.text.split(',')]
                keywords.extend(img_keywords)
                print(f"-> Gemini nhận diện: {img_keywords}")
        except Exception as e:
            print(f"[!] Lỗi khi xử lý Gemini Vision: {e}")

    # 2. Tách từ khóa từ Văn bản (Sử dụng Groq - Giữ nguyên logic của bạn)
    if user_input:
        print("--- Đang tách từ khóa từ văn bản... ---")
        prompt = f"Extract items from this text into a Python list: ['item']. Text: {user_input}"
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            res = completion.choices[0].message.content
            match = re.search(r"\[.*\]", res)
            if match:
                keywords.extend(ast.literal_eval(match.group()))
        except Exception as e:
            print(f"[!] Lỗi bóc tách text: {e}")
            
    # Làm sạch dữ liệu
    return list(set([k.lower().strip() for k in keywords if k and len(k) > 1]))

def generate_story(item_name, data_raw):
    """Sử dụng Groq để viết story (hoặc bạn có thể đổi sang Gemini tùy thích)"""
    prompt = f"Viết 1 đoạn văn ngắn 3 câu truyền cảm hứng về {item_name}. Gợi ý: {data_raw}"
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Không thể tạo story: {e}"