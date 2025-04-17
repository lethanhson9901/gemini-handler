# Gemini Handler 🚀

[![Giấy phép: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- [![Trạng thái Build](https://img.shields.io/travis/com/your-username/gemini-handler.svg)](https://travis-ci.com/your-username/gemini-handler) --> <!-- Cập nhật liên kết CI/CD nếu có -->

**Thư viện Python mạnh mẽ giúp tương tác hiệu quả với API Gemini của Google, tích hợp các tính năng quản lý API key thông minh, chiến lược xử lý lỗi linh hoạt, khả năng xử lý file, tạo đầu ra có cấu trúc, hỗ trợ proxy, và cung cấp một server tương thích OpenAI.**

`gemini-handler` đơn giản hóa các tác vụ phổ biến và tăng cường độ bền cho các ứng dụng sử dụng Gemini của bạn. Thư viện quản lý thông minh nhiều API key để giảm thiểu giới hạn tốc độ (rate limit), cung cấp nhiều chiến lược xử lý lỗi API, các phương thức tiện lợi cho việc tạo văn bản, tạo embedding, thao tác file, tạo dữ liệu có cấu trúc (JSON), và tích hợp dễ dàng với các hệ thống khác thông qua server API hoặc adapter LiteLLM.

## ✨ Tính năng nổi bật

*   **🤖 Hỗ trợ nhiều Model Gemini:** Tương tác với các model Gemini khác nhau cho tác vụ văn bản, embedding và hình ảnh (vision).
*   **🔑 Quản lý API Key Nâng cao:**
    *   Nạp key từ danh sách, biến môi trường (`GEMINI_API_KEY`, `GEMINI_API_KEYS`) hoặc file cấu hình YAML.
    *   Nhiều chiến lược luân chuyển key (`ROUND_ROBIN`, `SEQUENTIAL`, `LEAST_USED`, `SMART_COOLDOWN`) để phân phối tải và xử lý rate limit mượt mà.
    *   Tự động "làm mát" (cooldown) cho các key bị giới hạn tốc độ.
    *   Theo dõi thống kê sử dụng key (số lần dùng, lỗi, thời gian bị giới hạn).
*   **🔄 Tạo Nội dung Bền bỉ:**
    *   **Chiến lược Retry (Thử lại):** Tự động thử lại các yêu cầu thất bại với độ trễ có thể cấu hình.
    *   **Chiến lược Fallback (Dự phòng):** Thử tạo nội dung với một chuỗi các model nếu model chính thất bại.
    *   **Chiến lược Round Robin (Luân phiên):** Lần lượt thử qua các model có sẵn.
*   **📄 Đầu ra có cấu trúc (JSON):** Tạo nội dung tuân thủ nghiêm ngặt theo một JSON schema được cung cấp, tự động phân tích cú pháp JSON từ phản hồi.
*   **🖼️ Xử lý File:**
    *   Tải file cục bộ lên API Gemini.
    *   Quản lý các file đã tải lên (lấy thông tin, liệt kê, xóa).
    *   Tự động chờ file chuyển sang trạng thái `ACTIVE` trước khi sử dụng.
    *   Tải hàng loạt file từ một thư mục.
*   **👁️ Khả năng Vision:**
    *   Tạo nội dung dựa trên hình ảnh/file đã tải lên (tự động tải nội dung file khi cần).
    *   Tạo nội dung trực tiếp từ file hình ảnh cục bộ mà không cần tải lên trước.
*   **💡 Tạo Embedding:** Tạo embedding văn bản sử dụng các model embedding Gemini được chỉ định, hỗ trợ `task_type`.
*   **⚙️ Tùy chỉnh Linh hoạt:** Cấu hình các tham số tạo nội dung (temperature, top_p, v.v.) và `system_instruction`.
*   **📊 Phản hồi Chuẩn hóa:** Đối tượng `ModelResponse` nhất quán cho mọi kết quả, bao gồm trạng thái thành công, văn bản/dữ liệu, lỗi, thời gian xử lý, thông tin key và file đã sử dụng.
*   **🌐 Hỗ trợ Proxy:** Dễ dàng cấu hình HTTP/HTTPS proxy thông qua file cấu hình, tham số khởi tạo hoặc biến môi trường.
*   **🔌 Server Tương thích OpenAI:** Chạy một server API (FastAPI) với các endpoint `/v1/chat/completions`, `/v1/embeddings`, `/v1/models` tương tự OpenAI, cho phép tích hợp dễ dàng với các công cụ hiện có.
*   **🚀 Giao diện Dòng lệnh (CLI):** Khởi chạy server API nhanh chóng từ terminal.
*   **🧩 Tích hợp LiteLLM:** Adapter tích hợp sẵn để sử dụng `gemini-handler` như một custom provider trong LiteLLM.

## 🛠️ Cài đặt

Đảm bảo bạn đã cài đặt Python (>= 3.8).

1.  **Cài đặt thư viện cần thiết:**
    ```bash
    pip install google-generativeai PyYAML requests Pillow fastapi uvicorn litellm # Thêm litellm nếu cần
    ```
    *   `google-generativeai`: Thư viện chính thức của Google.
    *   `PyYAML`: Để đọc file cấu hình `.yaml`.
    *   `requests`: Được dùng nội bộ (ví dụ: tải file từ URI).
    *   `Pillow`: Để xử lý file hình ảnh cục bộ.
    *   `fastapi`, `uvicorn`: Để chạy server API tương thích OpenAI.
    *   `litellm`: Nếu bạn muốn sử dụng tích hợp LiteLLM.

2.  **Cài đặt `gemini-handler`:**
    *   **Từ mã nguồn (khuyến nghị hiện tại):**
        ```bash
        git clone https://github.com/lethanhson9901/gemini-handler.git # Thay bằng đường dẫn repo thực tế
        cd gemini-handler
        pip install -e .
        ```
    *   **(Khi được xuất bản)**
        ```bash
        # pip install gemini-handler
        ```

## 🔑 Cấu hình: API Keys và Proxy

`gemini-handler` cần các API key Google Gemini và có thể sử dụng proxy.

### API Keys

Thư viện sẽ nạp key theo thứ tự ưu tiên sau:

1.  **Danh sách key truyền trực tiếp (Code):** Cung cấp `api_keys=['key1', 'key2']` khi khởi tạo `GeminiHandler`.
2.  **File Cấu hình YAML:** Cung cấp `config_path="duong/dan/toi/config.yaml"` khi khởi tạo. File YAML cần có cấu trúc (xem ví dụ chi tiết bên dưới).
3.  **Biến Môi trường (Nhiều Keys):** Đặt biến `GEMINI_API_KEYS` là một chuỗi các key, phân tách bởi dấu phẩy:
    ```bash
    export GEMINI_API_KEYS="API_KEY_CUA_BAN_1,API_KEY_CUA_BAN_2,API_KEY_CUA_BAN_3"
    ```
4.  **Biến Môi trường (Một Key):** Đặt biến `GEMINI_API_KEY`:
    ```bash
    export GEMINI_API_KEY="API_KEY_DUY_NHAT_CUA_BAN"
    ```

Nếu không tìm thấy key nào qua các phương thức trên, thư viện sẽ báo lỗi `ValueError`.

### Proxy

Proxy có thể được cấu hình qua:

1.  **File Cấu hình YAML:** Xem mục `proxy` trong ví dụ YAML.
2.  **Tham số `proxy_settings` (Code):** Cung cấp dictionary `proxy_settings={'http': '...', 'https': '...'}` khi khởi tạo `GeminiHandler`.
3.  **Biến Môi trường:** Đặt biến `HTTP_PROXY` và `HTTPS_PROXY`. Biến môi trường sẽ **ghi đè** cài đặt từ file YAML hoặc tham số `proxy_settings`.
    ```bash
    export HTTP_PROXY="http://user:pass@your-proxy.com:port"
    export HTTPS_PROXY="http://user:pass@your-proxy.com:port" # Có thể giống http
    ```

### Cấu hình YAML Chi tiết (`config.yaml`)

Bạn có thể tùy chỉnh sâu hơn trong file `config.yaml`:

```yaml
# config.yaml ví dụ đầy đủ
gemini:
  # API Keys (bắt buộc)
  api_keys:
    - "AIzaSyBmWf7COPcA6r62lDUoZ3x0dp47iy7ttSk" # lethanhson99907
    - "AIzaSyAIsEdv54bT-UixRDnG5aoOGXbGaybPHMM" # lethanhson99908
    # - "..."

  # Cài đặt tạo nội dung mặc định (tùy chọn)
  generation:
    temperature: 0.7          # Độ sáng tạo (0.0-1.0)
    top_p: 1.0                # Ngưỡng xác suất tích lũy
    top_k: 40                 # Số token có xác suất cao nhất để xem xét
    max_output_tokens: 8192   # Độ dài tối đa phản hồi (token)
    stop_sequences: []        # Danh sách chuỗi dừng tạo nội dung
    response_mime_type: "text/plain" # Mặc định là text, dùng "application/json" cho structured output

  # Giới hạn tốc độ mặc định của key (tùy chọn) - Dùng cho KeyRotationManager
  rate_limits:
    requests_per_minute: 60   # Số request tối đa mỗi phút trên một key
    reset_window: 60          # Thời gian (giây) để bộ đếm request của key reset về 0

  # Chiến lược mặc định (tùy chọn) - Có thể override khi khởi tạo handler
  strategies:
    content: "round_robin"    # Chiến lược tạo nội dung ('round_robin', 'fallback', 'retry')
    key_rotation: "smart_cooldown" # Chiến lược luân chuyển key ('sequential', 'round_robin', 'least_used', 'smart_cooldown')

  # Cài đặt thử lại mặc định (tùy chọn) - Chỉ áp dụng cho chiến lược 'retry'
  retry:
    max_attempts: 3           # Số lần thử tối đa cho một yêu cầu lỗi
    delay: 30                 # Thời gian chờ (giây) giữa các lần thử

  # Model mặc định (tùy chọn)
  default_model: "gemini-2.0-flash" # Model dùng khi không chỉ định
  system_instruction: null      # System prompt mặc định

  # Cài đặt Embedding (tùy chọn)
  embedding:
    default_model: "gemini-embedding-exp-03-07" # Model embedding mặc định
    # Các tùy chọn khác có thể thêm ở đây nếu cần (ví dụ: task_type mặc định)
    # dimensions: 768 # Thông tin, không phải cài đặt trực tiếp
    # batch_size: 10 # Thông tin, không phải cài đặt trực tiếp
    # task_types: ... # Thông tin về các task type hỗ trợ

# Cài đặt Proxy (tùy chọn)
proxy:
  http: "http://brd-customer-hl_8d87b67a-zone-residential_proxy1:eb0e1vrv5v2g@brd.superproxy.io:33335"
  https: "https://brd-customer-hl_8d87b67a-zone-residential_proxy1:eb0e1vrv5v2g@brd.superproxy.io:33335"

# Cài đặt Server API (tùy chọn) - Các giá trị này có thể bị override bởi CLI args
# server:
#   host: "0.0.0.0"
#   port: 8000
#   workers: 1 # Số lượng worker (nếu dùng Gunicorn/Uvicorn nâng cao)
#   log_level: "info"
# security: # Cài đặt bảo mật cho server API
#   require_auth: false # Yêu cầu API key để truy cập server?
#   api_keys: [] # Danh sách các key hợp lệ nếu require_auth là true
```

## 🚀 Hướng dẫn sử dụng `GeminiHandler`

### 1. Khởi tạo Cơ bản

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy, GenerationConfig

# Khởi tạo đơn giản nhất (nạp key từ ENV hoặc config.yaml mặc định nếu có)
try:
    handler_default = GeminiHandler()
except ValueError as e:
    print(f"Lỗi: {e}. Vui lòng cấu hình API keys.")
    # Xử lý hoặc thoát

# Khởi tạo với danh sách key, chiến lược và proxy cụ thể
api_keys = ["API_KEY_CUA_BAN_1", "API_KEY_CUA_BAN_2"]
proxy_config = {
    'http': 'http://user:pass@proxy.example.com:8080',
    'https': 'http://user:pass@proxy.example.com:8080'
}
handler_custom = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.RETRY,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN,
    proxy_settings=proxy_config # Truyền cấu hình proxy
)

# Khởi tạo với file cấu hình và system instruction
system_instruction = "Bạn là một trợ lý AI hữu ích."
handler_with_config = GeminiHandler(
    config_path="config.yaml", # Đọc cả API keys và proxy từ file (nếu có)
    system_instruction=system_instruction
)

# Khởi tạo với cấu hình tạo nội dung mặc định khác
custom_gen_config = GenerationConfig(temperature=0.5, max_output_tokens=1000)
handler_with_gen_config = GeminiHandler(
    api_keys=api_keys,
    generation_config=custom_gen_config
)

# Gán handler bạn muốn sử dụng cho biến `handler`
handler = handler_with_config # Ví dụ: chọn handler đọc từ config
```

### 2. Tạo Nội dung Văn bản

```python
# Định nghĩa system prompt (nếu chưa có khi khởi tạo)
# handler.system_instruction = "Bạn là một chuyên gia..." # Có thể gán lại nếu cần

prompt = "Giải thích về điện toán đám mây cho người mới bắt đầu."
response = handler.generate_content(prompt=prompt) # Sử dụng system instruction đã gán

if response['success']:
    print("Văn bản được tạo:")
    print(response['text'])
    print(f"\nThời gian thực hiện: {response['time']:.2f}s")
    print(f"Index của API Key đã dùng: {response['api_key_index']}")
else:
    print(f"Lỗi khi tạo nội dung: {response['error']}")

# Tạo nội dung với model cụ thể và lấy thống kê key
response_detailed = handler.generate_content(
    prompt="Viết một đoạn văn ngắn về lợi ích của việc đọc sách.",
    model_name="gemini-1.5-flash", # Chỉ định model
    return_stats=True             # Lấy thống kê sử dụng key
)

if response_detailed['success']:
    print("\n" + response_detailed['text'])
    print("\nThống kê Key:")
    import json
    print(json.dumps(response_detailed['key_stats'], indent=2))
else:
    print(f"Lỗi: {response_detailed['error']}")
```

### 3. Tạo Dữ liệu có Cấu trúc (JSON)

```python
import json

# Định nghĩa cấu trúc JSON mong muốn (JSON Schema)
recipe_schema = {
    "type": "object",
    "properties": {
        "ten_mon_an": {"type": "string"},
        "nguyen_lieu": {"type": "array", "items": {"type": "string"}},
        "buoc_thuc_hien": {"type": "array", "items": {"type": "string"}},
        "thoi_gian_chuan_bi": {"type": "string", "description": "Ví dụ: 15 phút"},
        "thoi_gian_nau": {"type": "string", "description": "Ví dụ: 30 phút"}
    },
    "required": ["ten_mon_an", "nguyen_lieu", "buoc_thuc_hien"]
}

prompt = "Cho tôi công thức làm món phở bò Hà Nội đơn giản tại nhà."

# Tạo dữ liệu có cấu trúc
# Lưu ý: generate_structured_content tự động đặt response_mime_type="application/json"
result = handler.generate_structured_content(
    prompt=prompt,
    schema=recipe_schema,
    model_name="gemini-1.5-pro", # Nên dùng model mạnh hơn cho JSON phức tạp
    # temperature=0.2 # Có thể override tham số generation ở đây
)

if result['success'] and result['structured_data']:
    print("\nDữ liệu cấu trúc được tạo:")
    recipe = result['structured_data']
    print(json.dumps(recipe, indent=2, ensure_ascii=False))
    # print(f"\nVăn bản gốc từ API: {result['text']}") # Hữu ích để debug nếu JSON parse lỗi
elif result['success'] and not result['structured_data']:
     print(f"\nThành công nhưng không phân tích được JSON từ phản hồi:")
     print(result['text'])
     print(f"Lỗi phân tích (nếu có): {result['error']}")
else:
    print(f"\nLỗi khi tạo dữ liệu cấu trúc: {result['error']}")

```

### 4. Tạo Embedding

```python
from gemini_handler import EmbeddingConfig # Import để dùng hằng số task_type

# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

texts_to_embed = [
    "Cách mạng công nghiệp 4.0 là gì?",
    "Những ứng dụng chính của AI trong y tế.",
    "Python là ngôn ngữ lập trình phổ biến.",
]

# Tạo embedding đơn giản (sử dụng model và task type mặc định từ config)
response = handler.generate_embeddings(content=texts_to_embed)

if response['success']:
    print(f"\nĐã tạo {len(response['embeddings'])} embeddings.")
    # print(response['embeddings']) # Danh sách các vector embedding
    print(f"Vector đầu tiên có {len(response['embeddings'][0])} chiều.")
    print(f"Index của API Key đã dùng: {response['api_key_index']}")
else:
    print(f"\nLỗi khi tạo embeddings: {response['error']}")

# Tạo embedding với model và task_type cụ thể
response_specific = handler.generate_embeddings(
    content="Tìm kiếm tài liệu: thư viện Python tốt nhất cho web development",
    model_name="gemini-embedding-exp-03-07", # Chỉ định model embedding
    task_type=EmbeddingConfig.RETRIEVAL_QUERY, # Chỉ định loại tác vụ là truy vấn
    return_stats=True
)

# Các loại task_type khả dụng trong EmbeddingConfig:
# SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING, RETRIEVAL_DOCUMENT,
# RETRIEVAL_QUERY, QUESTION_ANSWERING, FACT_VERIFICATION, CODE_RETRIEVAL_QUERY

if response_specific['success']:
    print("\nEmbedding cho truy vấn tìm kiếm:")
    # print(response_specific['embeddings'])
    print("\nThống kê Key:")
    print(json.dumps(response_specific['key_stats'], indent=2))
else:
    print(f"Lỗi: {response_specific['error']}")
```

### 5. Thao tác với File (Upload, Quản lý, Sử dụng)

```python
from pathlib import Path
import time
import json # Để in đẹp

# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

# --- Tải File Lên ---
# file_path = "duong/dan/toi/hinh_anh_cua_ban.jpg" # Hoặc file PDF, video, audio... được hỗ trợ
file_path = Path("./cat_image.jpg") # Ví dụ: tạo file ảnh mèo để test
if not file_path.exists():
    # Tạo file ảnh giả nếu chưa có (cần Pillow)
    try:
        from PIL import Image
        img = Image.new('RGB', (60, 30), color = 'red')
        img.save(file_path)
        print(f"Đã tạo file ảnh giả: {file_path}")
    except ImportError:
        print("Lỗi: Cần cài Pillow để tạo ảnh giả (pip install Pillow)")
        # Xử lý lỗi hoặc thoát
        exit()
    except Exception as e:
         print(f"Lỗi khi tạo ảnh giả: {e}")
         exit()

print(f"\nĐang tải lên file: {file_path}...")
upload_result = handler.upload_file(file_path)

if upload_result['success']:
    uploaded_file_object = upload_result['file'] # Lấy đối tượng file gốc từ Google API
    uploaded_file_name = uploaded_file_object.name # Lấy tên file dạng "files/..."
    print(f"File tải lên thành công: {uploaded_file_name}")
    print(f"URI: {uploaded_file_object.uri}")
    print(f"Trạng thái ban đầu: {uploaded_file_object.state.name}") # Truy cập state.name

    # Chờ file được xử lý (quan trọng!)
    print("Đang chờ file xử lý...")
    active_file_object = None
    for _ in range(6): # Thử tối đa 6 lần (30 giây)
        get_result = handler.get_file(uploaded_file_name)
        if get_result['success']:
            current_file_object = get_result['file']
            print(f"  Trạng thái hiện tại: {current_file_object.state.name}")
            if current_file_object.state.name == "ACTIVE":
                active_file_object = current_file_object
                break # Thoát vòng lặp khi đã ACTIVE
            elif current_file_object.state.name == "FAILED":
                 print("Lỗi: File xử lý thất bại trên server.")
                 break
        else:
            print(f"Lỗi khi kiểm tra trạng thái file: {get_result['error']}")
            # Có thể break hoặc thử lại
        time.sleep(5) # Đợi 5 giây giữa các lần kiểm tra

    if active_file_object:
        print("File đã sẵn sàng để sử dụng.")

        # --- Lấy Thông tin File (đã có từ vòng lặp trên) ---
        print(f"\nThông tin file: {active_file_object.name}")
        print(f"  Trạng thái: {active_file_object.state.name}")
        print(f"  Loại MIME: {active_file_object.mime_type}")
        print(f"  Kích thước: {active_file_object.size_bytes} bytes")

        # --- Tạo Nội dung với File Đã Tải Lên (Văn bản) ---
        prompt_cho_file = "Mô tả chi tiết nội dung của hình ảnh này."
        # Sử dụng tên file hoặc đối tượng file đã lấy được
        file_gen_response = handler.generate_content_with_file(
            file=active_file_object, # Truyền đối tượng file đã ACTIVE
            prompt=prompt_cho_file,
            model_name="gemini-1.5-pro" # Bắt buộc dùng model vision
        )
        if file_gen_response['success']:
            print("\nNội dung được tạo từ File:")
            print(file_gen_response['text'])
            print(f"Thông tin file đã dùng: {file_gen_response['file_info']}")
        else:
            print(f"\nLỗi khi tạo nội dung từ file: {file_gen_response['error']}")

        # --- Tạo Nội dung với File Đã Tải Lên (JSON) ---
        image_schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "objects_detected": {"type": "array", "items": {"type": "string"}},
                "dominant_colors": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["description", "objects_detected"]
        }
        structured_file_gen_response = handler.generate_structured_content_with_file(
             file=active_file_object,
             prompt="Phân tích hình ảnh này và trích xuất thông tin theo cấu trúc yêu cầu.",
             schema=image_schema,
             model_name="gemini-1.5-pro" # Dùng model vision hỗ trợ JSON
        )
        if structured_file_gen_response['success'] and structured_file_gen_response['structured_data']:
            print("\nDữ liệu cấu trúc được tạo từ File:")
            print(json.dumps(structured_file_gen_response['structured_data'], indent=2, ensure_ascii=False))
        else:
            print(f"\nLỗi khi tạo dữ liệu cấu trúc từ file: {structured_file_gen_response['error']}")

        # --- Xóa File ---
        print(f"\nĐang xóa file: {uploaded_file_name}...")
        delete_result = handler.delete_file(uploaded_file_name)
        if delete_result['success']:
            print(f"Đã xóa thành công file: {delete_result['deleted_file']}")
        else:
            print(f"Lỗi khi xóa file: {delete_result['error']}")

    else:
        print(f"File không chuyển sang trạng thái ACTIVE sau khi chờ.")
        # Cân nhắc xóa file nếu xử lý lỗi hoặc không thành công
        # handler.delete_file(uploaded_file_name)

else:
    print(f"Lỗi khi tải file lên: {upload_result['error']}")

# --- Liệt kê Files ---
print("\nĐang liệt kê các file...")
list_result = handler.list_files(page_size=5) # Lấy tối đa 5 file mỗi trang
if list_result['success']:
    print("Danh sách Files:")
    if list_result['files']:
        for f in list_result['files']:
             # Truy cập state qua .name
             print(f" - {f['name']} ({f['mime_type']}, Trạng thái: {f['state'].name if f.get('state') else 'N/A'})")
        # if list_result['next_page_token']: # FileHandler hiện tại không trả token dễ dàng
        #     print(f"Còn trang tiếp theo (next_page_token): {list_result['next_page_token']}")
    else:
        print("  (Không có file nào)")
else:
    print(f"Lỗi khi liệt kê files: {list_result['error']}")

# --- Tải Hàng Loạt (Batch Upload) ---
# Tạo thư mục và file giả để ví dụ
batch_dir = Path("temp_upload_dir")
batch_dir.mkdir(exist_ok=True)
(batch_dir / "tai_lieu_1.txt").write_text("Nội dung file text 1.", encoding='utf-8')
(batch_dir / "hinh_anh_doc.png").touch() # Tạo file rỗng
(batch_dir / "script_util.py").write_text("print('Hello Utility')", encoding='utf-8')

print("\nĐang tải lên hàng loạt từ thư mục 'temp_upload_dir'...")
batch_result = handler.batch_upload_files(
    directory_path=batch_dir,
    file_extensions=['.txt', '.png'] # Chỉ tải file có đuôi .txt hoặc .png
)
if batch_result['success']:
    print(f"Đã tải lên thành công {batch_result['count']} files:")
    uploaded_batch_files = []
    for f_info in batch_result['files']:
        print(f" - {f_info['name']} ({f_info['mime_type']})")
        uploaded_batch_files.append(f_info['name']) # Lưu tên để xóa sau

    # Dọn dẹp các file vừa tải lên (ví dụ)
    print("\nĐang dọn dẹp các file vừa batch upload...")
    # for file_name_to_delete in uploaded_batch_files:
    #     try:
    #         # Chờ file ACTIVE trước khi xóa nếu cần dùng ngay
    #         # Hoặc xóa trực tiếp nếu không cần dùng
    #         # Cần vòng lặp chờ tương tự như upload đơn lẻ nếu muốn đảm bảo xóa được
    #         del_res = handler.delete_file(file_name_to_delete)
    #         if del_res['success']:
    #             print(f"  Đã xóa {file_name_to_delete}")
    #         else:
    #              print(f"  Lỗi xóa {file_name_to_delete}: {del_res['error']}")
    #     except Exception as e_del:
    #         print(f"  Lỗi ngoại lệ khi xóa {file_name_to_delete}: {e_del}")
else:
    print(f"Lỗi trong quá trình tải hàng loạt: {batch_result['error']}")

# Dọn dẹp thư mục tạm
import shutil
try:
    shutil.rmtree(batch_dir)
    print(f"\nĐã xóa thư mục tạm '{batch_dir}'.")
except OSError as e:
    print(f"Lỗi khi xóa thư mục tạm: {e}")

# Dọn dẹp file ảnh test ban đầu
try:
    file_path.unlink(missing_ok=True)
    print(f"Đã xóa file ảnh test '{file_path}'.")
except OSError as e:
    print(f"Lỗi khi xóa file ảnh test: {e}")
```

### 6. Tạo Nội dung với File Cục bộ (Không cần Upload)

Hữu ích cho việc phân tích nhanh hình ảnh cục bộ mà không cần lưu trữ chúng qua File API.

```python
from pathlib import Path
import json

# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

local_image_path = Path("./local_image.jpeg")
if not local_image_path.exists():
    # Tạo file ảnh giả nếu chưa có
    try:
        from PIL import Image
        img = Image.new('RGB', (80, 40), color = 'blue')
        img.save(local_image_path)
        print(f"Đã tạo file ảnh giả cục bộ: {local_image_path}")
    except ImportError:
        print("Lỗi: Cần cài Pillow để tạo ảnh giả (pip install Pillow)")
        exit()
    except Exception as e:
         print(f"Lỗi khi tạo ảnh giả: {e}")
         exit()

# --- Tạo Văn bản từ Ảnh Cục bộ ---
print(f"\nĐang tạo nội dung từ file cục bộ: {local_image_path}...")
local_gen_response = handler.generate_with_local_file(
    file_path=local_image_path,
    prompt="Có những đối tượng nào trong bức ảnh này?",
    model_name="gemini-1.5-pro" # Bắt buộc dùng model vision
)

if local_gen_response['success']:
    print("\nNội dung được tạo từ File Cục bộ:")
    print(local_gen_response['text'])
    print(f"Thông tin file: {local_gen_response['file_info']}")
else:
    print(f"\nLỗi khi tạo nội dung từ file cục bộ: {local_gen_response['error']}")

# --- Tạo JSON từ Ảnh Cục bộ ---
local_structured_response = handler.generate_with_local_file(
    file_path=local_image_path,
    prompt="Mô tả chủ thể chính và màu sắc chủ đạo của bức ảnh này.",
    schema={ # Ví dụ schema
        "type": "object",
        "properties": {
            "chu_the": {"type": "string"},
            "mau_sac": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["chu_the", "mau_sac"]
    },
    model_name="gemini-1.5-pro" # Dùng model vision hỗ trợ JSON
)

if local_structured_response['success'] and local_structured_response['structured_data']:
    print("\nDữ liệu cấu trúc được tạo từ File Cục bộ:")
    print(json.dumps(local_structured_response['structured_data'], indent=2, ensure_ascii=False))
else:
    print(f"\nLỗi khi tạo dữ liệu cấu trúc từ file cục bộ: {local_structured_response['error']}")

# Dọn dẹp file ảnh test cục bộ
try:
    local_image_path.unlink(missing_ok=True)
    print(f"\nĐã xóa file ảnh cục bộ test '{local_image_path}'.")
except OSError as e:
    print(f"Lỗi khi xóa file ảnh cục bộ test: {e}")

```

## 🚀 Chạy Server Tương thích OpenAI

Thư viện bao gồm một server API dựa trên FastAPI, cung cấp các endpoint tương tự OpenAI, cho phép tích hợp `gemini-handler` với các công cụ và ứng dụng hiện có hỗ trợ API của OpenAI.

### Chạy Server từ Dòng lệnh (CLI)

Cách dễ nhất để khởi chạy server là sử dụng CLI tích hợp:

```bash
python -m gemini_handler.cli --config config.yaml --port 8000
```

**Các tùy chọn CLI:**

*   `--host`: Địa chỉ IP để server lắng nghe (mặc định: `0.0.0.0`).
*   `--port`: Cổng để server lắng nghe (mặc định: `8000`).
*   `--keys`: Danh sách API key Gemini, phân tách bởi dấu phẩy (ví dụ: `"key1,key2"`). **Ưu tiên cao nhất**, sẽ ghi đè key từ config hoặc ENV.
*   `--config`: Đường dẫn đến file cấu hình YAML (mặc định: `config.yaml`). Server sẽ đọc các cài đặt như `api_keys`, `strategies`, `rate_limits`, `proxy`, `generation` từ file này (nếu không bị override bởi CLI args hoặc ENV).

Server sẽ tự động sử dụng các chiến lược, quản lý key, và hỗ trợ proxy đã được cấu hình thông qua file YAML hoặc các giá trị mặc định.

### Các Endpoints của Server

Server cung cấp các endpoint sau, tương thích với định dạng của OpenAI API v1:

*   **`GET /v1/models`**: Liệt kê danh sách các model Gemini được hỗ trợ bởi server (ví dụ: `gemini-1.5-pro`, `gemini-embedding-exp-03-07`).
*   **`POST /v1/chat/completions`**: Tạo phản hồi chat. Nhận vào request body tương tự OpenAI (với `model`, `messages`, `temperature`, `max_tokens`, `stream` (hiện chưa hỗ trợ), `response_format`={ "type": "json_object" }, v.v.). Server sẽ chuyển đổi `messages` thành prompt và gọi phương thức `generate_content` hoặc `generate_structured_content` của `GeminiHandler`.
*   **`POST /v1/embeddings`**: Tạo embeddings. Nhận vào request body tương tự OpenAI (với `model`, `input`). Server sẽ gọi phương thức `generate_embeddings` của `GeminiHandler`.
*   **`GET /health`**: Endpoint kiểm tra sức khỏe đơn giản, trả về `{"status": "ok"}`.

### Ví dụ Sử dụng Server (với `curl`)

```bash
# 1. Lấy danh sách models
curl http://localhost:8000/v1/models

# 2. Tạo chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [
      {"role": "system", "content": "Bạn là trợ lý."},
      {"role": "user", "content": "Viết câu chào buổi sáng."}
    ],
    "temperature": 0.7,
    "max_tokens": 50
  }'

# 3. Tạo chat completion yêu cầu JSON output
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [
      {"role": "user", "content": "Cho tôi thông tin về Paris dưới dạng JSON với key là city và country."}
    ],
    "response_format": { "type": "json_object" }
  }'


# 4. Tạo embeddings
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-embedding-exp-03-07",
    "input": "Văn bản cần tạo embedding"
  }'

# 5. Kiểm tra health
curl http://localhost:8000/health
```

## 🧩 Tích hợp với LiteLLM

Sử dụng `LiteLLMGeminiAdapter` để tích hợp `gemini-handler` như một custom provider trong LiteLLM. Điều này cho phép bạn tận dụng các tính năng quản lý key và chiến lược của `gemini-handler` trong môi trường LiteLLM.

### Cấu hình LiteLLM

Đăng ký provider tùy chỉnh trong code của bạn:

```python
import litellm
import os

# Đảm bảo gemini_handler đã được cài đặt
# Đăng ký provider, trỏ đến adapter class
litellm.register_provider(
    "custom_gemini",
    import_string="gemini_handler.LiteLLMGeminiAdapter" # Đường dẫn import chính xác
)

# ---- Cấu hình API Keys cho Adapter ----
# Ưu tiên 1: Đặt biến môi trường LiteLLM_GEMINI_API_KEY (LiteLLM khuyến nghị)
# os.environ["LITELLM_GEMINI_API_KEY"] = "key_cua_ban"

# Ưu tiên 2: Đặt biến môi trường GEMINI_API_KEYS (phân tách bởi dấu phẩy)
os.environ["GEMINI_API_KEYS"] = "AIzaSyBmWf7COPcA6r62lDUoZ3x0dp47iy7ttSk,AIzaSyAIsEdv54bT-UixRDnG5aoOGXbGaybPHMM"

# Ưu tiên 3: Đặt biến môi trường GEMINI_API_KEY
# os.environ["GEMINI_API_KEY"] = "key_cua_ban"

# Ưu tiên 4: Truyền trực tiếp khi gọi (ít khuyến khích hơn cho adapter dùng chung)
# api_key_param = "key_cua_ban"

# Lưu ý: Adapter sẽ chỉ khởi tạo handler một lần và tái sử dụng.
# Nó sẽ tìm key theo thứ tự: LITELLM_GEMINI_API_KEY -> GEMINI_API_KEYS -> GEMINI_API_KEY.
# Nếu bạn truyền api_key khi gọi litellm.completion, nó sẽ được ưu tiên cho *lần gọi đó*,
# nhưng không thay đổi handler dùng chung trừ khi handler chưa được khởi tạo.
```

### Sử dụng với LiteLLM

Gọi các hàm của LiteLLM, chỉ định model với tiền tố `custom_gemini/`:

```python
# --- Chat Completion ---
try:
    response = litellm.completion(
        model="custom_gemini/gemini-1.5-pro", # Sử dụng tiền tố đã đăng ký
        messages=[
            {"role": "user", "content": "Hello, how are you?"}
        ],
        temperature=0.5
        # api_key=api_key_param # Chỉ truyền nếu muốn override cho lần gọi này
    )
    print("\nLiteLLM Completion Response:")
    print(response)

    # Lấy nội dung trả về
    if response and response.choices and response.choices[0].message:
         print("\nContent:", response.choices[0].message.content)

except Exception as e:
    print(f"\nLỗi LiteLLM Completion: {e}")


# --- Embedding ---
try:
    embedding_response = litellm.embedding(
        model="custom_gemini/gemini-embedding-exp-03-07", # Sử dụng tiền tố
        input=["Your text to embed here", "Another text"]
        # api_key=api_key_param
    )
    print("\nLiteLLM Embedding Response:")
    # print(embedding_response)
    if embedding_response and embedding_response.data:
        print(f"Generated {len(embedding_response.data)} embeddings.")
        print(f"First embedding dimensions: {len(embedding_response.data[0].embedding)}")

except Exception as e:
    print(f"\nLỗi LiteLLM Embedding: {e}")

```

Adapter sẽ tự động chuyển đổi định dạng request/response giữa LiteLLM và `GeminiHandler`.

## 🎯 Các chiến lược

### Chiến lược tạo nội dung (`content_strategy`)

| Chiến lược         | Mô tả                                                                   | Khi nào sử dụng                                  |
| :----------------- | :---------------------------------------------------------------------- | :----------------------------------------------- |
| **`ROUND_ROBIN`**  | Sử dụng lần lượt các model trong danh sách `models` theo vòng tròn.       | Khi muốn phân tán tải đều cho các model.         |
| **`FALLBACK`**     | Thử model chỉ định (hoặc model đầu tiên), nếu lỗi thì thử model tiếp theo. | Khi cần độ tin cậy cao, ưu tiên model tốt nhất. |
| **`RETRY`**        | Thử lại cùng một model nhiều lần (theo `max_attempts`) khi gặp lỗi.        | Khi muốn nhất quán về model sử dụng cho 1 prompt. |

### Chiến lược luân chuyển API key (`key_strategy`)

| Chiến lược             | Mô tả                                                                                                | Khi nào sử dụng                                          |
| :--------------------- | :--------------------------------------------------------------------------------------------------- | :------------------------------------------------------- |
| **`SEQUENTIAL`**       | Sử dụng các key theo thứ tự trong danh sách, quay lại đầu khi hết.                                    | Đơn giản, khi muốn ưu tiên một số key nhất định.         |
| **`ROUND_ROBIN`**      | Sử dụng các key lần lượt theo vòng tròn, bỏ qua key bị rate limit hoặc không khả dụng.                 | Khi muốn phân bổ đều các request, dễ dự đoán.          |
| **`LEAST_USED`**       | Ưu tiên key có số lần sử dụng ít nhất trong khoảng `reset_window` và đang khả dụng.                   | Khi cần cân bằng tải thực tế giữa các key.               |
| **`SMART_COOLDOWN`**   | Tự động "làm mát" key bị rate limit, ưu tiên key ít lỗi và đã nghỉ lâu nhất trong số key khả dụng.   | Khi cần khả năng tự phục hồi cao, tối ưu khi key bị limit. |

## 💡 Sử dụng nâng cao

### Tùy chỉnh chiến lược khi khởi tạo

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy, GenerationConfig

# Khởi tạo với chiến lược tùy chỉnh và override generation config
handler_advanced = GeminiHandler(
    config_path="config.yaml", # Nạp keys, proxy từ file
    content_strategy=Strategy.FALLBACK,         # Dùng chiến lược dự phòng
    key_strategy=KeyRotationStrategy.LEAST_USED, # Dùng key ít sử dụng nhất
    generation_config=GenerationConfig(temperature=0.8, top_k=50) # Override generation
)
# Sử dụng handler_advanced cho các tác vụ tiếp theo
```

### Theo dõi hiệu suất Request

```python
import json
import time

# Tạo nội dung và yêu cầu trả về thống kê
response_perf = handler.generate_content(
    prompt="Viết một bài phân tích về xu hướng AI năm 2024",
    return_stats=True # Quan trọng: đặt là True
)

if response_perf['success']:
    print(response_perf['text'])
    print("-" * 20)
    print(f"Thời gian thực hiện: {response_perf['time']:.2f} giây")
    print(f"Model đã sử dụng: {response_perf['model']}")
    print(f"Index Key đã sử dụng: {response_perf['api_key_index']}")
    print(f"Số lần thử (nếu dùng Retry): {response_perf.get('attempts', 1)}") # attempts chỉ có ý nghĩa với Retry
    print("\nThống kê Key:")
    print(json.dumps(response_perf['key_stats'], indent=2))

else:
    print(f"Lỗi: {response_perf['error']}")
```

### Giám sát Tổng thể Sử dụng API key

```python
import json
import time
import datetime

# Lấy thống kê sử dụng cho tất cả các key
all_key_stats = handler.get_key_stats()

print("\nThống kê Tổng thể Sử dụng Key:")
print(json.dumps(all_key_stats, indent=2))

# Lấy thống kê cho một key cụ thể (ví dụ: key thứ 2 - index 1)
try:
    key_1_stats = handler.get_key_stats(key_index=1)
    print("\nThống kê cho Key Index 1:")
    print(json.dumps(key_1_stats, indent=2))
except (IndexError, ValueError) as e:
    print(f"\nKhông thể lấy thống kê cho key index 1: {e}")

# Hiển thị thông tin từng key một cách dễ đọc
print("\nChi tiết từng Key:")
for key_idx, stats in all_key_stats.items():
    print(f"  Key {key_idx}:")
    print(f"    Số lần sử dụng (trong window): {stats['uses']}")
    last_used_time_str = "Chưa sử dụng"
    if stats['last_used'] > 0:
        last_used_time_str = datetime.datetime.fromtimestamp(stats['last_used']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"    Lần cuối sử dụng: {last_used_time_str}")
    print(f"    Số lần thất bại liên tiếp: {stats['failures']}")
    rate_limited_until_time_str = "Không bị giới hạn"
    if stats['rate_limited_until'] > time.time():
        rate_limited_until_time_str = datetime.datetime.fromtimestamp(stats['rate_limited_until']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"    Bị giới hạn đến: {rate_limited_until_time_str}")
```

## ⚠️ Xử lý lỗi

Thư viện được thiết kế để xử lý lỗi một cách linh hoạt thông qua các chiến lược và quản lý key. Tuy nhiên, bạn vẫn cần kiểm tra kết quả trả về.

*   **Kiểm tra `response['success']` (boolean):** Đây là chỉ báo chính về thành công hay thất bại của yêu cầu *tổng thể*.
*   **Kiểm tra `response['error']`:** Nếu `success` là `False`, trường này sẽ chứa thông tin lỗi (ví dụ: "Max retries exceeded", "All models failed", "Rate limit exceeded", "Copyright material detected", lỗi API gốc, lỗi phân tích JSON).
*   **Lỗi Rate Limit (`429`):** `KeyRotationManager` sẽ tự động xử lý lỗi này bằng cách đánh dấu key là bị giới hạn và chọn key khác (dựa trên `key_strategy`). Nếu tất cả các key đều bị giới hạn, các chiến lược có thể thất bại và trả về lỗi.
*   **Lỗi Bản quyền:** Phản hồi bị chặn do vi phạm bản quyền (`finish_reason == 4` trong API response gốc) sẽ được `ResponseHandler` phát hiện và trả về `success=False` cùng thông báo lỗi cụ thể.
*   **Lỗi Phân tích JSON:** Khi yêu cầu đầu ra có cấu trúc (`response_mime_type="application/json"`), `ResponseHandler` sẽ cố gắng phân tích cú pháp phản hồi text thành JSON. Nếu thất bại, `success` sẽ là `False` và `error` sẽ chỉ ra lỗi phân tích.
*   **Lỗi File API:** Các lỗi liên quan đến tải lên, lấy hoặc xóa file sẽ được trả về trong dictionary kết quả của các phương thức `upload_file`, `get_file`, `delete_file`, v.v.
*   **`response['model']`:** Cho biết model cuối cùng được thử (có thể là model gây lỗi hoặc model fallback).
*   **`response['attempts']`:** Chỉ có ý nghĩa với chiến lược `RETRY`, cho biết số lần đã thử.

```python
# Ví dụ xử lý lỗi rõ ràng hơn
prompt_nguy_hiem = "Prompt vi phạm chính sách nội dung" # Ví dụ
response = handler.generate_content(prompt_nguy_hiem)

if response['success']:
    print("Thành công:")
    print(response['text'])
else:
    print("="*10 + " LỖI XẢY RA " + "="*10)
    print(f"Thông báo lỗi: {response['error']}")
    print(f"Model cuối cùng thử: {response['model']}")
    print(f"Index Key cuối cùng thử: {response['api_key_index']}")
    if 'attempts' in response: # Kiểm tra nếu có thông tin attempts
        print(f"Số lần thử (Retry strategy): {response['attempts']}")

    # Xử lý cụ thể dựa trên loại lỗi (ví dụ)
    if "Copyright material detected" in response['error']:
        print("-> Lỗi này do nội dung bản quyền, thử lại với prompt khác.")
    elif "Rate limit" in response['error']:
        print("-> Lỗi này do giới hạn request, hệ thống sẽ tự chuyển key.")
    elif "Failed to parse JSON" in response['error']:
        print("-> Lỗi này do model không trả về JSON hợp lệ, kiểm tra lại prompt hoặc schema.")
    # ... thêm các xử lý lỗi khác
```

## ⚙️ Sử dụng Biến Môi trường (Ngoài file YAML)

Bạn có thể cấu hình một số tham số chính thông qua biến môi trường. Chúng thường **ghi đè** các giá trị tương ứng trong file YAML (trừ `api_keys` có thứ tự ưu tiên riêng như đã nêu). Proxy cũng có thể bị ghi đè bởi `HTTP_PROXY`/`HTTPS_PROXY`.

```bash
# API Keys (ưu tiên cao hơn YAML nếu được đặt)
export GEMINI_API_KEYS="key1,key2,key3"
# export GEMINI_API_KEY="key-cua-ban" # Chỉ dùng nếu GEMINI_API_KEYS không có

# Proxy (sẽ ghi đè proxy trong YAML hoặc proxy_settings)
export HTTP_PROXY="http://proxy.server:port"
export HTTPS_PROXY="http://proxy.server:port"

# Cài đặt khác (ít dùng hơn, thường nên đặt trong YAML hoặc code)
# export GEMINI_DEFAULT_MODEL="gemini-1.5-pro"
# Các cài đặt như rate limit, strategies, retry thường được đặt trong YAML hoặc khi khởi tạo handler.
# Biến môi trường cho server CLI (nếu không dùng --args):
# export GEMINI_HOST="127.0.0.1"
# export GEMINI_PORT="9000"
```

**Lưu ý:** Việc sử dụng biến môi trường tiện lợi cho cấu hình đơn giản hoặc trong môi trường container, nhưng file YAML cung cấp khả năng cấu hình chi tiết và có cấu trúc hơn.

## 🚀 Ví dụ thực tế: Xây dựng Chatbot Bền bỉ

Ví dụ này sử dụng `GeminiHandler` với các chiến lược phù hợp để tạo ra một chatbot có khả năng xử lý lỗi và rate limit tốt hơn.

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy
import sys
import time

# Khởi tạo handler với chiến lược tối ưu cho chatbot
try:
    chatbot_handler = GeminiHandler(
        config_path="config.yaml", # Đảm bảo file này tồn tại và có key, proxy nếu cần
        content_strategy=Strategy.FALLBACK, # Ưu tiên model tốt, fallback nếu lỗi
        key_strategy=KeyRotationStrategy.SMART_COOLDOWN, # Xử lý rate limit tốt
        system_instruction="Bạn là một trợ lý ảo thân thiện và hữu ích tên là GemiBot."
    )
    print("GemiBot: Đã khởi tạo thành công!")
    # In thống kê key ban đầu (tùy chọn)
    # print("Thống kê key ban đầu:", json.dumps(chatbot_handler.get_key_stats(), indent=2))
except ValueError as e:
    print(f"Lỗi khởi tạo GeminiHandler: {e}")
    print("Vui lòng kiểm tra cấu hình API key trong config.yaml hoặc biến môi trường.")
    sys.exit(1) # Thoát nếu không có key
except FileNotFoundError:
    print("Lỗi: Không tìm thấy file config.yaml. Đang thử khởi tạo không có config...")
    try:
         chatbot_handler = GeminiHandler(
            # Thử nạp key từ ENV
            content_strategy=Strategy.FALLBACK,
            key_strategy=KeyRotationStrategy.SMART_COOLDOWN,
            system_instruction="Bạn là một trợ lý ảo thân thiện và hữu ích tên là GemiBot."
         )
         print("GemiBot: Đã khởi tạo thành công (sử dụng API keys từ ENV).")
    except ValueError as e_env:
        print(f"Lỗi khởi tạo GeminiHandler từ ENV: {e_env}")
        sys.exit(1)


def chat_with_user():
    print("\nGemiBot: Xin chào! Tôi có thể giúp gì cho bạn? (Gõ 'tạm biệt' để thoát)")
    conversation_history = [] # Lưu trữ lịch sử dưới dạng [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["tạm biệt", "bye", "exit", "quit"]:
            print("GemiBot: Tạm biệt! Hẹn gặp lại!")
            break

        # Thêm tin nhắn người dùng vào lịch sử
        conversation_history.append({"role": "user", "content": user_input})

        # Tạo prompt từ lịch sử (đơn giản, chỉ nối chuỗi)
        # Có thể cải tiến để phù hợp hơn với cách model xử lý ngữ cảnh
        prompt_parts = []
        if chatbot_handler.system_instruction:
             prompt_parts.append(f"System: {chatbot_handler.system_instruction}")
        for msg in conversation_history:
             role = msg["role"]
             content = msg["content"]
             if role == "user":
                 prompt_parts.append(f"User: {content}")
             elif role == "assistant":
                 prompt_parts.append(f"Assistant: {content}")
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:" # Yêu cầu model đóng vai Assistant


        # Tạo phản hồi với xử lý lỗi tích hợp
        # Chiến lược Fallback sẽ tự động thử model khác nếu cần
        # model_to_try = "gemini-1.5-pro" # Ưu tiên model mạnh (nếu có trong config.models)
        model_to_try = chatbot_handler.config.default_model # Sử dụng model mặc định

        print("GemiBot: (Đang suy nghĩ...)")
        start_time = time.time()
        response = chatbot_handler.generate_content(
            prompt=prompt,
            model_name=model_to_try,
            return_stats=True # Lấy thống kê để debug
        )
        end_time = time.time()
        print(f"GemiBot: (Thời gian phản hồi: {end_time - start_time:.2f}s, Key: {response.get('api_key_index', 'N/A')})")


        # Hiển thị kết quả hoặc thông báo lỗi cuối cùng
        if response['success']:
            bot_reply = response['text'].strip()
            print(f"GemiBot: {bot_reply}")
            # Thêm phản hồi của bot vào lịch sử
            conversation_history.append({"role": "assistant", "content": bot_reply})
        else:
            error_msg = response['error']
            key_index = response.get('api_key_index', 'N/A')
            model_failed = response.get('model', 'N/A')
            print(f"GemiBot: Xin lỗi, tôi đang gặp chút vấn đề kỹ thuật.")
            print(f"  Lỗi: {error_msg}")
            print(f"  (Model: {model_failed}, Key Index: {key_index})")

            # Xóa lượt hỏi của người dùng khỏi lịch sử nếu bot lỗi, tránh lặp lại
            if conversation_history and conversation_history[-1]["role"] == "user":
                 conversation_history.pop()
            print("GemiBot: Vui lòng thử lại sau giây lát hoặc đặt câu hỏi khác.")

        # Giới hạn lịch sử để tránh prompt quá dài (ví dụ: giữ 10 cặp thoại gần nhất)
        MAX_HISTORY_PAIRS = 10
        if len(conversation_history) > MAX_HISTORY_PAIRS * 2:
             conversation_history = conversation_history[-(MAX_HISTORY_PAIRS * 2):]

        # In thống kê key sau mỗi vài lượt (tùy chọn)
        # if len(conversation_history) % 4 == 0: # Ví dụ: in sau mỗi 2 lượt thoại
        #      print("\n--- Key Stats ---")
        #      print(json.dumps(chatbot_handler.get_key_stats(), indent=2))
        #      print("-----------------\n")


# Chạy chatbot
if __name__ == "__main__":
    chat_with_user()
```

## 🧩 Các Thành phần Chính

*   **`GeminiHandler`:** Class chính, là điểm truy cập cho mọi tương tác. Quản lý cấu hình, key, chiến lược, và gọi các API Gemini. Kế thừa từ `ContentGenerationMixin` và `FileOperationsMixin`.
*   **`ContentGenerationMixin`:** Chứa các phương thức tạo nội dung (`generate_content`, `generate_structured_content`, `generate_embeddings`).
*   **`FileOperationsMixin`:** Chứa các phương thức liên quan đến file (`upload_file`, `get_file`, `list_files`, `delete_file`, `batch_upload_files`, `generate_content_with_file`, `generate_structured_content_with_file`, `generate_with_local_file`).
*   **`Strategy` (Enum):** Định nghĩa các chiến lược tạo nội dung (`ROUND_ROBIN`, `FALLBACK`, `RETRY`).
*   **`KeyRotationStrategy` (Enum):** Định nghĩa các chiến lược luân chuyển API key (`SEQUENTIAL`, `ROUND_ROBIN`, `LEAST_USED`, `SMART_COOLDOWN`).
*   **`GenerationConfig`:** Dataclass để cấu hình tham số model như `temperature`, `top_p`, `max_output_tokens`, `response_mime_type`, `response_schema`.
*   **`EmbeddingConfig`:** Dataclass cho tham số embedding, bao gồm hằng số `task_type`.
*   **`ModelResponse`:** Dataclass chuẩn hóa cho kết quả gọi API, chứa `success` (bool), `model` (str), `text` (str), `structured_data` (dict), `embeddings` (list), `error` (str), `time` (float), `api_key_index` (int), `file_info` (dict).
*   **`KeyRotationManager`:** Xử lý logic chọn, theo dõi trạng thái và luân chuyển API key dựa trên chiến lược và rate limit.
*   **`FileHandler`:** Lớp cấp thấp hơn chuyên xử lý tương tác với Gemini File API (upload, get, list, delete). Được `GeminiHandler` sử dụng nội bộ.
*   **`EmbeddingHandler`:** Lớp chuyên xử lý việc gọi API embedding, sử dụng `KeyRotationManager`.
*   **`ResponseHandler`:** Xử lý và chuẩn hóa phản hồi thô từ API Gemini, bao gồm kiểm tra lỗi bản quyền và phân tích JSON.
*   **`strategies.py`:** Chứa các class triển khai `ContentStrategy` (RoundRobinStrategy, FallbackStrategy, RetryStrategy).
*   **`config.py` (`ConfigLoader`):** Tiện ích nạp API key và proxy từ nhiều nguồn cho `GeminiHandler`.
*   **`proxy.py` (`ProxyManager`):** Quản lý cấu hình proxy cho các request HTTP.
*   **`server.py` (`GeminiServer`):** Implement server FastAPI tương thích OpenAI.
*   **`cli.py`:** Giao diện dòng lệnh để khởi chạy `GeminiServer`.
*   **`litellm_integration.py` (`LiteLLMGeminiAdapter`):** Adapter để tích hợp với LiteLLM.
*   **`config_loader.py` (`ServerConfig`):** (Ít dùng trực tiếp) Lớp cấu hình riêng cho server, nhưng `cli.py` hiện đang đọc YAML trực tiếp.

## 📄 Giấy phép

Dự án này được phát hành theo Giấy phép MIT - xem file `LICENSE` để biết thêm chi tiết. (Bạn nên tạo file `LICENSE` chứa nội dung giấy phép MIT nếu chưa có).

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo Pull Request hoặc mở Issue nếu bạn có ý tưởng cải tiến hoặc phát hiện lỗi.

Quy trình đóng góp đề xuất:
1.  Fork kho lưu trữ.
2.  Tạo một nhánh mới (`git checkout -b feature/ten-tinh-nang-cua-ban`).
3.  Thực hiện các thay đổi của bạn.
4.  Thêm unit test cho các thay đổi (nếu có thể).
5.  Đảm bảo tất cả các test đều pass.
6.  Format code của bạn (ví dụ: dùng Black, Flake8).
7.  Commit các thay đổi (`git commit -m 'Them tinh nang X'`).
8.  Push lên nhánh (`git push origin feature/ten-tinh-nang-cua-ban`).
9.  Mở một Pull Request.
