import os
import ast
import re
import time
import base64
import redis # Thêm Redis
import hashlib # Thêm Hash để tạo key
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Retry & Timeout
MAX_RETRIES = 3
RETRY_DELAY = 2.0
API_TIMEOUT = 120.0

# Khởi tạo Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Các model sử dụng
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Khởi tạo Redis Client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"), 
    port=6379, 
    db=0, 
    decode_responses=True
)
CACHE_TTL = 604800 # Thời gian sống của cache: 7 ngày (tính bằng giây)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_input(user_input=None, image_path=None):
    keywords = []
    
    # 1. Nhận diện từ Hình ảnh (Sử dụng Groq Vision)
    if image_path:
        print(f"--- Đang phân tích ảnh bằng Groq Vision ({GROQ_VISION_MODEL}): {os.path.basename(image_path)} ---")
        try:
            base64_image = encode_image(image_path)
            prompt_vision = "Hãy nhìn vào ảnh này và liệt kê tên các món đồ vật chính có trong ảnh bằng Tiếng Việt. Trả về ĐÚNG định dạng danh sách Python, ví dụ: ['nón lá', 'áo dài']. Không giải thích thêm."
            
            for attempt in range(MAX_RETRIES):
                try:
                    completion = groq_client.chat.completions.create(
                        model=GROQ_VISION_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt_vision},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        temperature=0,
                        timeout=API_TIMEOUT
                    )
                    res = completion.choices[0].message.content
                    match = re.search(r"\[.*?\]", res, flags=re.DOTALL)
                    if match:
                        img_keywords_vn = ast.literal_eval(match.group())
                        keywords.extend(img_keywords_vn)
                        print(f"-> Groq Vision nhận diện (Tiếng Việt): {img_keywords_vn}")
                    break
                except Exception as e:
                    print(f"[!] Lỗi phân tích ảnh bằng Groq Vision (Lần {attempt + 1}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"[!] Lỗi xử lý ảnh: {e}")

    # 2. Tách từ khóa từ Văn bản (Sử dụng Groq - Giữ nguyên logic của bạn)
    if user_input:
        print("--- Đang tách từ khóa từ văn bản... ---")
        prompt = f"Extract items from this text into a Python list: ['item']. Text: {user_input}"
        
        for attempt in range(MAX_RETRIES):
            try:
                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    timeout=API_TIMEOUT
                )
                res = completion.choices[0].message.content
                match = re.search(r"\[.*?\]", res, flags=re.DOTALL)
                if match:
                    keywords.extend(ast.literal_eval(match.group()))
                break  # Nếu thành công thì thoát vòng lặp retry
            except Exception as e:
                print(f"[!] Lỗi bóc tách text bằng Groq (Lần {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
            
    # Làm sạch dữ liệu
    return list({k.lower().strip() for k in keywords if k and len(k) > 1})

def generate_story(item_name, data_raw):
    # 1. Tạo một mã băm (hash) duy nhất làm Key Cache dựa trên tên sản phẩm
    cache_key = f"story:{hashlib.md5(item_name.encode('utf-8')).hexdigest()}"
    try:
        # 2. KIỂM TRA CACHE TRƯỚC
        cached_story = redis_client.get(cache_key)
        if cached_story:
            print(f"[Cache HIT] Lấy story cho '{item_name}' từ bộ nhớ đệm Redis ⚡")
            return cached_story
    except Exception as e:
        print(f"[Cảnh báo] Lỗi kết nối Redis: {e}")

    """Sử dụng Groq để viết story (hoặc bạn có thể đổi sang Gemini tùy thích)"""
    prompt = f"Viết 1 đoạn văn ngắn 3 câu truyền cảm hứng về {item_name}. Gợi ý: {data_raw}"
    
    for attempt in range(MAX_RETRIES):
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                timeout=API_TIMEOUT
            )
            res = completion.choices[0].message.content
            try:
                redis_client.setex(cache_key, CACHE_TTL, res)
            except Exception:
                pass # Bỏ qua lỗi lưu cache nếu Redis sập
            return res
        except Exception as e:
            print(f"[!] Lỗi tạo story (Lần {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                
    return "Rất tiếc, hệ thống không thể tải được câu chuyện văn hoá vào lúc này do lỗi kết nối."