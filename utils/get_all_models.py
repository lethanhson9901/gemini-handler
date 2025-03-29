import os
import re

import google.generativeai as genai
import yaml

# Đọc API key từ file config.yaml
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')

try:
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
        api_key = "AIzaSyBAbbiFb2-PtPXZYnpHLK3RU-07D6xPo5Q"  # Sử dụng API key từ yêu cầu của bạn
except Exception as e:
    print(f"Lỗi khi đọc file config: {e}")
    api_key = "AIzaSyBAbbiFb2-PtPXZYnpHLK3RU-07D6xPo5Q"  # Sử dụng API key từ yêu cầu của bạn

# Cấu hình API key
genai.configure(api_key=api_key)

# Liệt kê tất cả model có sẵn
try:
    models = genai.list_models()
    
    # Lọc các model Gemini và định dạng lại output
    formatted_models = []
    for model in models:
        if "gemini" in model.name.lower() or "imagen" in model.name.lower():
            # Trích xuất tên model từ đường dẫn đầy đủ (models/gemini-xxx)
            model_name = model.name.split('/')[-1]
            
            # Bỏ qua các phiên bản cụ thể (như -001, -002) và -latest
            if re.search(r'-(00\d|latest)$', model_name):
                continue
                
            # Bỏ qua các model trùng lặp
            if model_name not in formatted_models:
                formatted_models.append(model_name)
    
    # Thêm imagen-3.0-generate-002 nếu cần
    if "imagen-3.0-generate-002" not in formatted_models:
        formatted_models.append("imagen-3.0-generate-002")
    
    # Sắp xếp models theo ưu tiên (đặt các model cụ thể lên đầu)
    priority_order = {
        "gemini-2.0-flash": 0,
        "gemini-2.5-pro-exp-03-25": 1,
        "gemini-2.0-flash-lite": 2,
        "gemini-2.0-pro-exp-02-05": 3,
        "gemini-1.5-flash": 4,
        "gemini-1.5-flash-8b": 5,
        "gemini-1.5-pro": 6,
        "gemini-embedding-exp-03-07": 7,
        "imagen-3.0-generate-002": 8,
        "gemini-2.0-flash-thinking-exp-01-21": 9,
        "gemini-exp-1206": 10
    }
    
    # Sắp xếp theo thứ tự ưu tiên
    formatted_models.sort(key=lambda x: priority_order.get(x, 999))
    
    # In ra định dạng mong muốn
    print("[")
    for i, model in enumerate(formatted_models):
        comma = "," if i < len(formatted_models) - 1 else ""
        print(f'    "{model}"{comma}')
    print("]")
    
except Exception as e:
    print(f"Lỗi khi lấy danh sách model: {e}")
