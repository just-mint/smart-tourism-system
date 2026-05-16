import os
import httpx
import json
from sqlalchemy.orm import Session
from app.domains.agent import schema

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "search_culture",
                "description": "Tìm kiếm thông tin địa điểm (tọa độ lat/lon, id, loại) khi người dùng hỏi về một địa danh.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "keyword": {
                            "type": "STRING",
                            "description": "Tên địa điểm cần tìm."
                        }
                    },
                    "required": ["keyword"]
                }
            },
            {
                "name": "check_weather",
                "description": "Lấy thời tiết tại một tọa độ cụ thể.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "lat": {"type": "NUMBER"},
                        "lon": {"type": "NUMBER"}
                    },
                    "required": ["lat", "lon"]
                }
            },
            {
                "name": "search_products",
                "description": "Tìm kiếm sản phẩm O2O (ví dụ: áo dài, cà phê, nón lá) để gợi ý mua sắm.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "keyword": {
                            "type": "STRING",
                            "description": "Tên sản phẩm cần tìm."
                        }
                    },
                    "required": ["keyword"]
                }
            },
            {
                "name": "find_stores_near",
                "description": "Tìm các cửa hàng quanh một tọa độ cụ thể để khách mua sắm.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "lat": {"type": "NUMBER"},
                        "lon": {"type": "NUMBER"},
                        "radius": {
                            "type": "NUMBER",
                            "description": "Bán kính tìm kiếm bằng mét (mặc định 2000)"
                        }
                    },
                    "required": ["lat", "lon"]
                }
            },
            {
                "name": "create_itinerary",
                "description": "Tự động tạo lộ trình mua sắm tối ưu O2O từ vị trí và nhu cầu của khách. Gọi khi khách muốn lên kế hoạch đi mua sắm, tìm đường, hoặc hỏi nên đi đâu mua gì.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "lat": {"type": "NUMBER", "description": "Vĩ độ vị trí xuất phát"},
                        "lon": {"type": "NUMBER", "description": "Kinh độ vị trí xuất phát"},
                        "keywords": {"type": "STRING", "description": "Từ khóa mua sắm, vd: lụa, nón lá, café"},
                        "radius": {"type": "NUMBER", "description": "Bán kính tìm kiếm mét (mặc định 3000)"},
                        "max_budget": {"type": "NUMBER", "description": "Ngân sách tối đa VNĐ (optional)"}
                    },
                    "required": ["lat", "lon", "keywords"]
                }
            }
        ]
    }
]

async def execute_tool(db: Session, function_name: str, args: dict):
    print(f"[Agent] Đang thực thi Tool ngầm: {function_name} | Tham số: {args}")

    def parse_coordinates(args_dict):
        try:
            lat = float(args_dict.get("lat"))
            lon = float(args_dict.get("lon"))
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("Tọa độ ngoài phạm vi hợp lệ")
            return lat, lon
        except (TypeError, ValueError):
            return None, None
        
    if function_name == "search_culture":
        keyword = args.get("keyword", "").strip()
        if not keyword: return {"status": "error", "message": "keyword is empty hoặc không hợp lệ"}

        from app.domains.culture.service import search_places_by_name
        results = search_places_by_name(db, keyword)
        if not results: return {"status": "not_found", "message": "Không có địa danh nào khớp, hãy bảo khách cung cấp lại tên."}
        
        places = []
        for p in results[:3]:
            # Đảm bảo xử lý an toàn kiểu Numeric trả về int/float
            try:
                lat = float(p.lat) if p.lat is not None else 0.0
                lon = float(p.lon) if p.lon is not None else 0.0
            except:
                lat, lon = (0.0, 0.0)
            places.append({"id": p.id, "name": p.name, "lat": lat, "lon": lon})
            
        return {"status": "success", "places": places}
        
    elif function_name == "check_weather":
        lat, lon = parse_coordinates(args)
        if lat is None: return {"status": "error", "message": "lat/lon bị thiếu hoặc sai định dạng"}
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    cw = r.json().get("current_weather", {})
                    code = cw.get("weathercode")
                    # Dịch WMO Code sang tiếng Việt cho AI dễ mường tượng
                    cond = "Quang đãng"
                    if code in [61, 63, 65, 80, 81, 82]: cond = "Trời mưa"
                    elif code in [95, 96, 99]: cond = "Có bão sấm sét"
                    elif code in [1, 2, 3]: cond = "Nhiều Mây"
                    
                    return {
                        "temperature": cw.get("temperature"), 
                        "condition": cond, 
                        "windspeed": cw.get("windspeed")
                    }
        except:
            return {"error": "Mạng bị đứt đoạn không thể check thời tiết"}
            
    elif function_name == "search_products":
        keyword = args.get("keyword", "").strip()
        if not keyword: return {"status": "error", "message": "keyword is empty hoặc không hợp lệ"}
        from app.domains.inventory.model import Product
        products = db.query(Product).filter(Product.name.ilike(f"%{keyword}%")).limit(5).all()
        if not products: return {"status": "not_found", "message": "Không có sản phẩm nào khớp."}
        
        result = []
        for p in products:
            result.append({"product_id": p.product_id, "name": p.name, "price": p.price})
        return {"status": "success", "products": result}

    elif function_name == "find_stores_near":
        lat, lon = parse_coordinates(args)
        if lat is None: return {"status": "error", "message": "lat/lon bị thiếu hoặc sai định dạng"}
        
        try:
            radius = int(args.get("radius", 2000))
            if radius <= 0: radius = 2000
        except (TypeError, ValueError):
            radius = 2000 # Fallback về default nếu AI truyền bậy

        from app.domains.inventory.model import Store
        from sqlalchemy import func
        from sqlalchemy.sql import text
        
        # Use simple coordinate bounding box or PostGIS ST_DWithin
        point = f"SRID=4326;POINT({lon} {lat})"
        stores = db.query(Store).filter(
            func.ST_DWithin(Store.geom, func.ST_GeogFromText(point), radius)
        ).limit(5).all()
        
        if not stores: return {"status": "not_found", "message": "Không có cửa hàng nào gần đó."}
        
        result = []
        for s in stores:
            result.append({"store_id": s.store_id, "name": s.name, "category": s.category, "address": s.address})
        return {"status": "success", "stores": result}
        
    elif function_name == "create_itinerary":
        lat, lon = parse_coordinates(args)
        if lat is None: return {"status": "error", "message": "lat/lon bị thiếu hoặc sai định dạng"}
        
        keywords = str(args.get("keywords", "")).strip()
        if not keywords: return {"status": "error", "message": "Bắt buộc phải có keywords mua sắm"}
        
        try:
            radius = int(args.get("radius", 3000))
        except (TypeError, ValueError):
            radius = 3000
            
        try:
            max_budget_raw = args.get("max_budget")
            max_budget = int(max_budget_raw) if max_budget_raw is not None else None
        except (TypeError, ValueError):
            max_budget = None
            
        from app.domains.planner.service import generate_smart_itinerary
        from app.domains.planner.schema import PlannerRequest
        
        try:
            req = PlannerRequest(
                current_lat=lat, current_lon=lon,
                radius=radius, keywords=keywords,
                top_n=5,
                max_budget=int(max_budget) if max_budget else None,
            )
            result = await generate_smart_itinerary(db, req)
            
            if not result.optimized_route:
                return {"status": "no_results", "message": "Không tìm thấy cửa hàng phù hợp trong khu vực."}
            
            stops = []
            for stop in result.optimized_route:
                stops.append({
                    "order": stop.order,
                    "name": stop.name,
                    "category": stop.category,
                    "rating": stop.rating,
                    "distance_km": stop.distance_km,
                    "products_count": len(stop.products),
                })
            
            return {
                "status": "success",
                "total_stops": len(stops),
                "total_distance_km": result.metrics.total_distance_km,
                "stops": stops,
                "weather": result.weather.condition if result.weather else None,
                "message": "Lộ trình đã được tạo! Khách có thể xem chi tiết trên tab Itinerary."
            }
        except Exception as e:
            return {"status": "error", "message": f"Lỗi tạo lộ trình: {str(e)}"}
        
    return {"error": f"Unknown tool: {function_name}"}

async def chat_with_agent(db: Session, request: schema.AgentChatRequest):
    from app.core.config import settings
    api_key = settings.GEMINI_API_KEY
    internal_actions = []
    bot_answer = "Oh, có lỗi xảy ra hoặc tôi đang bảo trì. Vui lòng thử lại sau!"
    
    if not api_key:
        return schema.AgentChatResponse(answer="Bot thiếu API Key.", internal_actions=[])
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Ép Gemini tuân thủ tư duy O2O Agent
    sys_instruction_text = "Bạn là AEGIS AI, chuyên gia du lịch và gợi ý mua sắm O2O tại Việt Nam. Nếu khách hỏi địa danh, BẮT BUỘC gọi hàm search_culture. Nếu khách muốn mua sắm, BẮT BUỘC gọi search_products hoặc find_stores_near. Nếu khách muốn lên kế hoạch, tìm đường đi mua sắm, hoặc hỏi 'nên đi đâu', BẮT BUỘC gọi create_itinerary với tọa độ và từ khóa. Luôn khuyến khích khách 'Giữ hàng (Lock)' qua giao diện O2O và xem lộ trình trên tab Itinerary."
    # P1-26: NHÚNG TỌA ĐỘ VÀO SYSTEM PROMPT
    # Kiểm tra xem request có gửi lên tọa độ không, nếu có thì chép thẳng vào não Agent
    lat = getattr(request, 'lat', None)
    lon = getattr(request, 'lon', None)
    if lat is not None and lon is not None:
        sys_instruction_text += f"\n\n[QUAN TRỌNG]: Tọa độ hiện tại của người dùng là Vĩ độ {lat}, Kinh độ {lon}. BẮT BUỘC ưu tiên sử dụng tọa độ này làm tham số mặc định khi gọi các tool 'find_stores_near', 'check_weather' và 'create_itinerary'."
    # ---------------------------------------------
    
    system_instruction = {"parts": [{"text": sys_instruction_text}]}
    
    history = [
        {"role": "user", "parts": [{"text": request.query}]}
    ]

    max_loops = 5
    loop = 0
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        while loop < max_loops:
            loop += 1
            payload = {
                "systemInstruction": system_instruction,
                "contents": history,
                "tools": TOOLS
            }
            
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                bot_answer = f"Lỗi gọi Gemini API: {res.text}"
                break
                
            resp_data = res.json()
            candidates = resp_data.get("candidates", [])
            if not candidates: break
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts: break
            
            # Gemini trả về Function Call hay trả Text?
            function_call = None
            text_answer = None
            
            for part in parts:
                if "functionCall" in part:
                    function_call = part["functionCall"]
                if "text" in part:
                    text_answer = part["text"]
                    
            # Chèn phản hồi của máy vào lịch sử hội thoại chuẩn form The Gemini SDK
            model_resp = {"role": "model", "parts": parts}
            history.append(model_resp)
            
            # Nếu AI yêu cầu Tool -> Lập tức chạy Local Code
            if function_call:
                f_name = function_call.get("name")
                f_args = function_call.get("args", {})
                
                # Tracking
                internal_actions.append(f"{f_name}({f_args})")
                
                f_res = await execute_tool(db, f_name, f_args)
                
                # Trả response ngược lại cho Model dưới dạng role "user" part "functionResponse" hoặc role "function"  -> Theo Spec của Google là array parts
                func_response_msg = {
                    "role": "user", 
                    "parts": [{
                        "functionResponse": {
                            "name": f_name,
                            "response": {"name": f_name, "content": f_res}
                        }
                    }]
                }
                history.append(func_response_msg)
                
                # Loop round tiếp theo cho mô hình đọc `functionResponse`
                continue
                
            # Nếu mô hình trả String Text Answer thì Kết Thúc!
            if text_answer:
                bot_answer = text_answer
                break
                
    return schema.AgentChatResponse(
        answer=bot_answer,
        internal_actions=internal_actions
    )
