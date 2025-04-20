# Gemini Handler 🚀

[![Giấy phép: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- [![Trạng thái Build](https://img.shields.io/travis/com/your-username/gemini-handler.svg)](https://travis-ci.com/your-username/gemini-handler) --> <!-- Cập nhật liên kết CI/CD nếu có -->
[![PyPI version](https://badge.fury.io/py/gemini-handler.svg)](https://badge.fury.io/py/gemini-handler) <!-- Thêm nếu có trên PyPI -->

**Thư viện Python mạnh mẽ giúp tương tác hiệu quả với API Gemini của Google, tích hợp các tính năng quản lý API key thông minh, chiến lược xử lý lỗi linh hoạt, khả năng xử lý file, tạo đầu ra có cấu trúc, hỗ trợ proxy nâng cao (bao gồm tự động luân chuyển), và cung cấp một server tương thích OpenAI.**

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
    *   **Mới:** Tạo nội dung trực tiếp từ file hình ảnh cục bộ mà không cần tải lên trước.
*   **💡 Tạo Embedding:** Tạo embedding văn bản sử dụng các model embedding Gemini được chỉ định, hỗ trợ `task_type`.
*   **⚙️ Tùy chỉnh Linh hoạt:** Cấu hình các tham số tạo nội dung (temperature, top_p, v.v.) và `system_instruction`.
*   **📊 Phản hồi Chuẩn hóa:** Đối tượng `ModelResponse` nhất quán cho mọi kết quả, bao gồm trạng thái thành công, văn bản/dữ liệu, lỗi, thời gian xử lý, thông tin key, file và **proxy** đã sử dụng.
*   **🌐 Hỗ trợ Proxy Nâng cao:**
    *   Dễ dàng cấu hình HTTP/HTTPS proxy tĩnh thông qua file cấu hình, tham số khởi tạo hoặc biến môi trường.
    *   **Mới:** Hỗ trợ **Tự động Luân chuyển Proxy** bằng cách tích hợp với thư viện [SwiftShadow](https://github.com/your-repo/swiftshadow) (nếu được cài đặt). Tự động cập nhật và xoay vòng qua danh sách proxy.
*   **🔌 Server Tương thích OpenAI:**
    *   Chạy một server API (FastAPI) với các endpoint `/v1/chat/completions`, `/v1/embeddings`, `/v1/models` tương tự OpenAI.
    *   Tự động luân chuyển proxy cho mỗi request đến các endpoint `/v1/*` (nếu proxy được cấu hình).
    *   **Mới:** Bao gồm thông tin proxy (đã ẩn thông tin nhạy cảm) trong phản hồi của endpoint `/v1/chat/completions`.
    *   **Mới:** Cung cấp các endpoint quản lý proxy: `/v1/proxy/info`, `/v1/proxy/stats`, `/v1/proxy/rotate`.
*   **🚀 Giao diện Dòng lệnh (CLI):** Khởi chạy server API nhanh chóng từ terminal, hỗ trợ cấu hình proxy và **kích hoạt auto-proxy**.
*   **🧩 Tích hợp LiteLLM:** Adapter tích hợp sẵn để sử dụng `gemini-handler` như một custom provider trong LiteLLM, bao gồm cả thông tin proxy trong phản hồi.

## 🛠️ Cài đặt

Đảm bảo bạn đã cài đặt Python (>= 3.8).

1.  **Cài đặt `gemini-handler`:**
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

2.  **(Tùy chọn) Cài đặt SwiftShadow cho Auto-Proxy:**
    Nếu bạn muốn sử dụng tính năng tự động luân chuyển proxy, hãy cài đặt SwiftShadow:
    ```bash
    pip install swiftshadow # Hoặc theo hướng dẫn cài đặt của SwiftShadow
    ```
    Nếu SwiftShadow không được cài đặt, các tính năng auto-proxy sẽ bị vô hiệu hóa nhưng proxy tĩnh vẫn hoạt động.

## 🔑 Cấu hình: API Keys và Proxy

`gemini-handler` cần các API key Google Gemini và có thể sử dụng proxy.

### API Keys

Thư viện sẽ nạp key theo thứ tự ưu tiên sau (nguồn đầu tiên tìm thấy sẽ được sử dụng):

1.  **Tham số `api_keys` (Code):** Cung cấp danh sách `api_keys=['key1', 'key2']` khi khởi tạo `GeminiHandler`. **Ưu tiên cao nhất khi khởi tạo trực tiếp `GeminiHandler`**.
2.  **File Cấu hình YAML:** Cung cấp `config_path="path/to/config.yaml"` khi khởi tạo. Xem cấu trúc bên dưới.
3.  **Biến Môi trường `GEMINI_API_KEYS`:** Chuỗi các key, phân tách bởi dấu phẩy (ví dụ: `"key1,key2,key3"`).
4.  **Biến Môi trường `GEMINI_API_KEY`:** Một API key duy nhất.

**Lưu ý cho Server CLI:** Khi chạy server từ CLI (`python -m gemini_handler.cli`), thứ tự ưu tiên là:
1.  Tham số `--keys` (CLI).
2.  File Cấu hình YAML (`--config`).
3.  Biến Môi trường (như trên, được `GeminiHandler` nạp nếu không có trong CLI hoặc config).

### Proxy

Proxy có thể được cấu hình qua nhiều nguồn, với thứ tự ưu tiên sau (nguồn đầu tiên tìm thấy sẽ được sử dụng):

1.  **Tham số `proxy_settings` (Code):** Cung cấp dictionary `proxy_settings={'http': '...', 'https': '...', 'auto_proxy': {...}}` khi khởi tạo `GeminiHandler`. **Ưu tiên cao nhất khi khởi tạo trực tiếp `GeminiHandler`**. Nếu bạn truyền `None` hoặc `{}` cho tham số này, nó sẽ **ghi đè** mọi cấu hình proxy từ file hoặc ENV, nghĩa là **không sử dụng proxy**.
2.  **Biến Môi trường:** Đặt biến `HTTP_PROXY` và `HTTPS_PROXY`. **Ưu tiên cao hơn** file cấu hình.
    ```bash
    export HTTP_PROXY="http://user:pass@your-proxy.com:port"
    export HTTPS_PROXY="http://user:pass@your-proxy.com:port" # Có thể giống http
    ```
3.  **File Cấu hình YAML:** Xem mục `proxy` trong ví dụ YAML.

**Tóm lại:**
*   Đối với `GeminiHandler` khởi tạo trực tiếp: Tham số `proxy_settings` > Biến môi trường > File YAML.
*   Đối với `GeminiServer` (qua CLI): Biến môi trường > File YAML. CLI flag `--auto-proxy` có thể *bật* auto-proxy nếu chưa có trong YAML.

### Cấu hình YAML Chi tiết (`config.yaml`)

```yaml
# config.yaml ví dụ đầy đủ
gemini:
  # API Keys (bắt buộc nếu không cung cấp qua code hoặc ENV)
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
  default_model: "gemini-1.5-flash" # Model dùng khi không chỉ định
  system_instruction: null      # System prompt mặc định

  # Cài đặt Embedding (tùy chọn)
  embedding:
    default_model: "gemini-embedding-exp-03-07" # Model embedding mặc định

# Cài đặt Proxy (tùy chọn)
proxy:
  # Proxy tĩnh (sẽ bị ghi đè bởi biến môi trường HTTP_PROXY/HTTPS_PROXY)
  http: "http://user:pass@static-proxy.com:port"
  https: "http://user:pass@static-proxy.com:port"

  # --- Cấu hình Auto Proxy (Yêu cầu cài đặt SwiftShadow) ---
  # Nếu mục 'auto_proxy' này tồn tại và SwiftShadow được cài đặt,
  # cấu hình proxy tĩnh ở trên sẽ bị bỏ qua.
  # auto_proxy:
  #   auto_update: true       # Tự động cập nhật danh sách proxy từ SwiftShadow? (mặc định: false)
  #   auto_rotate: true       # Tự động xoay vòng qua các proxy khả dụng? (mặc định: true)
  #   update_interval: 30     # Thời gian (giây) giữa các lần tự động cập nhật (mặc định: 15)

# Cài đặt Server API (tùy chọn) - Các giá trị này có thể bị override bởi CLI args hoặc ENV
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

# Khởi tạo với danh sách key, chiến lược và proxy tĩnh cụ thể
api_keys = ["API_KEY_CUA_BAN_1", "API_KEY_CUA_BAN_2"]
proxy_config_static = {
    'http': 'http://user:pass@proxy.example.com:8080',
    'https': 'http://user:pass@proxy.example.com:8080'
}
handler_custom = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.RETRY,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN,
    proxy_settings=proxy_config_static # Truyền cấu hình proxy tĩnh
)

# Khởi tạo với file cấu hình (đọc keys, proxy, strategies, etc. từ file)
system_instruction = "Bạn là một trợ lý AI hữu ích."
handler_with_config = GeminiHandler(
    config_path="config.yaml",
    system_instruction=system_instruction
)

# Khởi tạo với cấu hình Auto Proxy (Yêu cầu SwiftShadow)
# Lưu ý: proxy_settings sẽ override proxy trong config.yaml
proxy_config_auto = {
    'auto_proxy': {
        'auto_update': True,
        'auto_rotate': True,
        'update_interval': 60 # Cập nhật mỗi 60s
    }
    # Không cần 'http'/'https' ở đây nếu dùng auto_proxy
}
try:
    # Cần cài swiftshadow để chạy dòng này thành công
    handler_auto_proxy = GeminiHandler(
        api_keys=api_keys,
        proxy_settings=proxy_config_auto
    )
    print("Đã khởi tạo handler với Auto Proxy.")
except ImportError:
    print("Lỗi: SwiftShadow chưa được cài đặt. Không thể kích hoạt Auto Proxy.")
    # Có thể fallback về proxy tĩnh hoặc không proxy
    handler_auto_proxy = GeminiHandler(api_keys=api_keys) # Ví dụ: không proxy
except Exception as e_auto:
    print(f"Lỗi khi khởi tạo Auto Proxy: {e_auto}")
    handler_auto_proxy = GeminiHandler(api_keys=api_keys)

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
    # In thông tin proxy đã dùng (nếu có)
    if response.get('proxy_info'):
        print(f"Proxy đã dùng: {response['proxy_info'].get('proxy_string', 'N/A')}")
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
    if response_detailed.get('proxy_info'):
        print(f"Proxy đã dùng: {response_detailed['proxy_info'].get('proxy_string', 'N/A')}")
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
    if result.get('proxy_info'):
        print(f"Proxy đã dùng: {result['proxy_info'].get('proxy_string', 'N/A')}")
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
import json # Để in đẹp

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
    # Embedding handler chưa trả về proxy_info trong response này
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
        time.sleep(5) # Đợi 5 giây giữa các lần kiểm tra

    if active_file_object:
        print("File đã sẵn sàng để sử dụng.")

        # --- Tạo Nội dung với File Đã Tải Lên (Văn bản) ---
        prompt_cho_file = "Mô tả chi tiết nội dung của hình ảnh này."
        file_gen_response = handler.generate_content_with_file(
            file=active_file_object, # Truyền đối tượng file đã ACTIVE
            prompt=prompt_cho_file,
            model_name="gemini-1.5-pro" # Bắt buộc dùng model vision
        )
        if file_gen_response['success']:
            print("\nNội dung được tạo từ File:")
            print(file_gen_response['text'])
            print(f"Thông tin file đã dùng: {file_gen_response['file_info']}")
            if file_gen_response.get('proxy_info'):
                 print(f"Proxy đã dùng: {file_gen_response['proxy_info'].get('proxy_string', 'N/A')}")
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
            if structured_file_gen_response.get('proxy_info'):
                 print(f"Proxy đã dùng: {structured_file_gen_response['proxy_info'].get('proxy_string', 'N/A')}")
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

else:
    print(f"Lỗi khi tải file lên: {upload_result['error']}")

# --- Liệt kê Files ---
# ... (Giống ví dụ trước)

# --- Tải Hàng Loạt (Batch Upload) ---
# ... (Giống ví dụ trước)

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
    if local_gen_response.get('proxy_info'):
         print(f"Proxy đã dùng: {local_gen_response['proxy_info'].get('proxy_string', 'N/A')}")
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
    if local_structured_response.get('proxy_info'):
         print(f"Proxy đã dùng: {local_structured_response['proxy_info'].get('proxy_string', 'N/A')}")
else:
    print(f"\nLỗi khi tạo dữ liệu cấu trúc từ file cục bộ: {local_structured_response['error']}")

# Dọn dẹp file ảnh test cục bộ
try:
    local_image_path.unlink(missing_ok=True)
    print(f"\nĐã xóa file ảnh cục bộ test '{local_image_path}'.")
except OSError as e:
    print(f"Lỗi khi xóa file ảnh cục bộ test: {e}")

```

## 🌐 Tự động Luân chuyển Proxy (SwiftShadow)

Nếu bạn đã cài đặt `swiftshadow` và cấu hình `auto_proxy` trong `proxy_settings` (qua code hoặc YAML), `gemini-handler` sẽ tự động:

1.  **Lấy danh sách proxy:** Sử dụng SwiftShadow để lấy danh sách proxy HTTP/HTTPS khả dụng.
2.  **Tự động cập nhật (tùy chọn):** Nếu `auto_update: true`, một luồng nền sẽ định kỳ gọi SwiftShadow để làm mới danh sách proxy.
3.  **Tự động luân chuyển (tùy chọn):** Nếu `auto_rotate: true` (mặc định), mỗi khi cần proxy (ví dụ: trong server middleware hoặc trước khi gọi API trực tiếp nếu không qua server), `ProxyManager` sẽ chọn proxy tiếp theo từ danh sách khả dụng theo vòng tròn.
4.  **Áp dụng Proxy:** Proxy được chọn sẽ được áp dụng vào biến môi trường (`HTTP_PROXY`, `HTTPS_PROXY`) để thư viện `google-generativeai` tự động sử dụng.

### Kích hoạt Auto-Proxy

**Cách 1: Qua tham số `proxy_settings` trong code:**

```python
# Yêu cầu: pip install swiftshadow
proxy_config_auto = {
    'auto_proxy': {
        'auto_update': True,
        'auto_rotate': True,
        'update_interval': 60 # Cập nhật mỗi 60s
    }
}
handler = GeminiHandler(api_keys=..., proxy_settings=proxy_config_auto)
```

**Cách 2: Qua file `config.yaml`:**

```yaml
# config.yaml
# ... (các phần khác)
proxy:
  # Proxy tĩnh bị bỏ qua nếu auto_proxy được định nghĩa và swiftshadow có sẵn
  # http: ...
  # https: ...
  auto_proxy:
    auto_update: true
    auto_rotate: true
    update_interval: 30
```
```python
# Khởi tạo handler đọc từ config
handler = GeminiHandler(config_path="config.yaml")
```

**Cách 3: Qua CLI khi chạy Server:**

Sử dụng cờ `--auto-proxy`. Cờ này sẽ **bật** `auto_rotate: true` và `auto_update: true` với `update_interval: 15` **nếu** `auto_proxy` chưa được định nghĩa trong file `config.yaml`. Nếu `auto_proxy` đã có trong config, cờ này không có tác dụng ghi đè cài đặt trong config.

```bash
# Yêu cầu: pip install swiftshadow
# Sử dụng keys/proxy từ config.yaml, nhưng bật auto-proxy nếu chưa có trong config
python -m gemini_handler.cli --config config.yaml --auto-proxy
```

**Lưu ý:** Tính năng này phụ thuộc hoàn toàn vào thư viện `swiftshadow`. Hãy đảm bảo `swiftshadow` được cài đặt và cấu hình đúng cách (nếu cần) để cung cấp proxy.

## 🚀 Chạy Server Tương thích OpenAI

Thư viện bao gồm một server API dựa trên FastAPI, cung cấp các endpoint tương tự OpenAI, cho phép tích hợp `gemini-handler` với các công cụ và ứng dụng hiện có hỗ trợ API của OpenAI.

### Chạy Server từ Dòng lệnh (CLI)

Cách dễ nhất để khởi chạy server là sử dụng CLI tích hợp:

```bash
# Chạy với cấu hình từ config.yaml và cổng 8000
python -m gemini_handler.cli --config config.yaml --port 8000

# Chạy và bật auto-proxy (nếu chưa có trong config và swiftshadow đã cài)
python -m gemini_handler.cli --config config.yaml --port 8000 --auto-proxy

# Chạy và override API keys từ CLI
python -m gemini_handler.cli --config config.yaml --port 8000 --keys "key1_cli,key2_cli"
```

**Các tùy chọn CLI:**

*   `--host`: Địa chỉ IP để server lắng nghe (mặc định: `0.0.0.0`).
*   `--port`: Cổng để server lắng nghe (mặc định: `8000`).
*   `--keys`: Danh sách API key Gemini, phân tách bởi dấu phẩy. **Ưu tiên cao nhất**, ghi đè key từ config hoặc ENV.
*   `--config`: Đường dẫn đến file cấu hình YAML (mặc định: `config.yaml`). Server đọc cài đặt từ đây.
*   `--auto-proxy`: Cờ để bật tính năng tự động luân chuyển proxy (yêu cầu `swiftshadow`). Chỉ có tác dụng nếu `auto_proxy` chưa được định nghĩa trong `config.yaml`.

Server sẽ tự động sử dụng các chiến lược, quản lý key, và hỗ trợ proxy (tĩnh hoặc tự động) đã được cấu hình. Một **middleware** sẽ tự động gọi `ProxyManager.apply_next_proxy()` trước mỗi request đến các endpoint `/v1/*` để luân chuyển proxy (nếu được cấu hình).

### Các Endpoints của Server

Server cung cấp các endpoint sau, tương thích với định dạng của OpenAI API v1:

*   **`GET /v1/models`**: Liệt kê danh sách các model Gemini được hỗ trợ.
*   **`POST /v1/chat/completions`**: Tạo phản hồi chat. Nhận request body tương tự OpenAI.
    *   Hỗ trợ `response_format={ "type": "json_object" }`.
    *   **Trả về thông tin proxy đã sử dụng** (đã ẩn thông tin nhạy cảm) trong trường `proxy_info` của response.
*   **`POST /v1/embeddings`**: Tạo embeddings. Nhận request body tương tự OpenAI.
*   **`GET /health`**: Endpoint kiểm tra sức khỏe đơn giản.
*   **`GET /v1/proxy/info`**: (Mới) Lấy thông tin về proxy đang được cấu hình (tĩnh hoặc trạng thái auto-proxy). Trả về proxy hiện tại (đã ẩn thông tin nhạy cảm).
*   **`GET /v1/proxy/stats`**: (Mới) Lấy thống kê chi tiết về việc sử dụng proxy, bao gồm trạng thái auto-proxy, số lượng proxy, proxy hiện tại, và lịch sử proxy gần đây (đã ẩn thông tin nhạy cảm).
*   **`POST /v1/proxy/rotate`**: (Mới) Kích hoạt thủ công việc chuyển sang proxy tiếp theo trong danh sách (nếu đang dùng auto-proxy hoặc có nhiều proxy tĩnh - hiện tại chủ yếu hữu ích cho auto-proxy). Trả về proxy mới được chọn.

### Ví dụ Sử dụng Server (với `curl`)

```bash
# 1. Lấy danh sách models
curl http://localhost:8000/v1/models

# 2. Tạo chat completion (sẽ tự động dùng proxy nếu server cấu hình)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [{"role": "user", "content": "Viết câu chào buổi sáng."}],
    "temperature": 0.7
  }'
# --> Kiểm tra trường "proxy_info" trong kết quả trả về

# 3. Tạo chat completion yêu cầu JSON output
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [{"role": "user", "content": "Thông tin Paris (JSON: city, country)."}],
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

# 6. Lấy thông tin proxy hiện tại (đã ẩn thông tin nhạy cảm)
curl http://localhost:8000/v1/proxy/info

# 7. Lấy thống kê proxy (đã ẩn thông tin nhạy cảm)
curl http://localhost:8000/v1/proxy/stats

# 8. Xoay vòng proxy thủ công (chủ yếu cho auto-proxy)
curl -X POST http://localhost:8000/v1/proxy/rotate
```

## 🧩 Tích hợp với LiteLLM

Sử dụng `LiteLLMGeminiAdapter` để tích hợp `gemini-handler` như một custom provider trong LiteLLM.

### Cấu hình LiteLLM

```python
import litellm
import os
import json # Để in đẹp

# Đăng ký provider
litellm.register_provider(
    "custom_gemini",
    import_string="gemini_handler.LiteLLMGeminiAdapter"
)

# ---- Cấu hình API Keys cho Adapter ----
# Adapter sẽ tìm key theo thứ tự:
# 1. Biến môi trường LITELLM_GEMINI_API_KEY (nếu có)
# 2. Biến môi trường GEMINI_API_KEYS (nếu có)
# 3. Biến môi trường GEMINI_API_KEY (nếu có)
# Đặt một trong các biến môi trường này
os.environ["GEMINI_API_KEYS"] = "KEY_1,KEY_2" # Ví dụ

# Lưu ý: Proxy sẽ được handler nạp từ ENV hoặc config.yaml như bình thường.
# Bạn không cần cấu hình proxy riêng cho adapter LiteLLM.
```

### Sử dụng với LiteLLM

```python
# --- Chat Completion ---
try:
    response = litellm.completion(
        model="custom_gemini/gemini-1.5-pro",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.5
    )
    print("\nLiteLLM Completion Response:")
    # In response dạng dictionary để xem cả proxy_info (nếu có)
    print(json.dumps(response.dict(), indent=2))

    # Lấy nội dung
    if response.choices:
         print("\nContent:", response.choices[0].message.content)
    # Kiểm tra proxy_info
    if response.get("proxy_info"):
         print("\nProxy Info (from LiteLLM response):", response["proxy_info"])

except Exception as e:
    print(f"\nLỗi LiteLLM Completion: {e}")


# --- Embedding ---
try:
    embedding_response = litellm.embedding(
        model="custom_gemini/gemini-embedding-exp-03-07",
        input=["Your text", "Another text"]
    )
    print("\nLiteLLM Embedding Response:")
    print(json.dumps(embedding_response.dict(), indent=2))
    if embedding_response.data:
        print(f"\nGenerated {len(embedding_response.data)} embeddings.")

except Exception as e:
    print(f"\nLỗi LiteLLM Embedding: {e}")
```

Adapter sẽ tự động chuyển đổi định dạng request/response và **bao gồm cả thông tin proxy** (đã ẩn thông tin nhạy cảm) trong phản hồi completion nếu có.

## 🎯 Các chiến lược

(Phần này giữ nguyên như trong README gốc)

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

(Giữ nguyên ví dụ)

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
    print(f"Số lần thử (nếu dùng Retry): {response_perf.get('attempts', 1)}")
    # In thông tin proxy nếu có
    if response_perf.get('proxy_info'):
        print(f"Proxy đã dùng: {response_perf['proxy_info'].get('proxy_string', 'N/A')}")
    print("\nThống kê Key:")
    print(json.dumps(response_perf['key_stats'], indent=2))

else:
    print(f"Lỗi: {response_perf['error']}")
    if response_perf.get('proxy_info'): # In cả proxy khi lỗi
        print(f"Proxy đã dùng khi lỗi: {response_perf['proxy_info'].get('proxy_string', 'N/A')}")

```

### Giám sát Tổng thể Sử dụng API key

(Giữ nguyên ví dụ)

### Giám sát Proxy (nếu dùng Handler trực tiếp)

```python
import json

# Lấy thông tin proxy hiện tại và thống kê từ handler
# Lưu ý: Thông tin này phản ánh trạng thái proxy của instance handler hiện tại.
# Nếu dùng server, các endpoint /v1/proxy/* sẽ tiện hơn.
proxy_details = handler.get_proxy_info()

print("\nThông tin Proxy từ Handler:")
print(json.dumps(proxy_details, indent=2))

# Ví dụ truy cập thông tin cụ thể
if proxy_details.get('current_proxy'):
    print(f"\nProxy hiện tại (Handler): {proxy_details['current_proxy'].get('proxy_string', 'N/A')}")
    print(f"Nguồn proxy: {proxy_details['current_proxy'].get('source', 'N/A')}") # 'static' hoặc 'auto'
print(f"Đang sử dụng Auto Proxy: {proxy_details.get('using_auto_proxy', False)}")

if proxy_details.get('stats'):
    print(f"Số lượng proxy khả dụng (ước tính): {proxy_details['stats'].get('proxy_count', 0)}")
    print("\nLịch sử Proxy (gần đây nhất):")
    for p_hist in proxy_details.get('proxy_history', [])[-5:]: # Lấy 5 proxy cuối
        if p_hist:
             print(f"  - {p_hist.get('proxy_string', 'N/A')} (Nguồn: {p_hist.get('source', 'N/A')})")

```

## ⚠️ Xử lý lỗi

Thư viện được thiết kế để xử lý lỗi một cách linh hoạt. Hãy kiểm tra `response['success']` và `response['error']`.

*   **Kiểm tra `response['success']` (boolean):** Chỉ báo chính về thành công/thất bại.
*   **Kiểm tra `response['error']`:** Chứa thông tin lỗi (ví dụ: "Max retries exceeded", "Rate limit exceeded", "Blocked: ... safety settings", "Failed to parse JSON response", lỗi API gốc, lỗi proxy/kết nối).
*   **Lỗi Rate Limit (`429`):** `KeyRotationManager` tự động xử lý. Nếu tất cả key đều bị giới hạn, bạn sẽ nhận lỗi.
*   **Lỗi Nội dung/Bản quyền/An toàn:** `ResponseHandler` phát hiện các lỗi chặn từ API (ví dụ: `finish_reason == 4` hoặc `prompt_feedback.block_reason`) và trả về `success=False` với thông báo lỗi cụ thể.
*   **Lỗi Phân tích JSON:** Nếu yêu cầu JSON (`response_mime_type="application/json"`) nhưng API không trả về JSON hợp lệ, `success` sẽ `False` và `error` sẽ là "Failed to parse JSON response". `response['text']` vẫn chứa phản hồi gốc từ API.
*   **Lỗi File API:** Trả về trong dictionary kết quả của các phương thức file.
*   **Lỗi Proxy/Kết nối:** Các lỗi như `ConnectionError`, `Timeout`, lỗi xác thực proxy sẽ được bắt và trả về trong `response['error']`, thường kèm theo thông tin proxy đã thử.
*   **`response['proxy_info']`:** Chứa thông tin về proxy đã được sử dụng cho request đó (nếu có), hữu ích để debug lỗi kết nối.

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
    print(f"Model cuối cùng thử: {response.get('model', 'N/A')}")
    print(f"Index Key cuối cùng thử: {response.get('api_key_index', 'N/A')}")
    if response.get('proxy_info'):
        print(f"Proxy đã dùng khi lỗi: {response.get('proxy_info').get('proxy_string', 'N/A')}")
    if 'attempts' in response:
        print(f"Số lần thử (Retry strategy): {response['attempts']}")

    # Xử lý cụ thể dựa trên loại lỗi
    if "Blocked: Response stopped due to safety settings" in response['error']:
        print("-> Lỗi này do nội dung bị chặn (bản quyền, an toàn), thử lại với prompt khác.")
    elif "Blocked: Prompt blocked due to safety settings" in response['error']:
        print("-> Lỗi này do prompt bị chặn, hãy sửa lại prompt.")
    elif "Rate limit" in response['error']:
        print("-> Lỗi này do giới hạn request, hệ thống sẽ tự chuyển key.")
    elif "Failed to parse JSON" in response['error']:
        print("-> Lỗi này do model không trả về JSON hợp lệ.")
        print(f"   Phản hồi gốc: {response.get('text', '')}") # In phản hồi gốc để xem
    elif "Connection/Proxy Error" in response['error']:
         print("-> Lỗi kết nối hoặc proxy. Kiểm tra cài đặt proxy và kết nối mạng.")
    # ... thêm các xử lý lỗi khác
```

## ⚙️ Sử dụng Biến Môi trường (Ngoài file YAML)

Bạn có thể cấu hình một số tham số chính thông qua biến môi trường.

*   **API Keys:** `GEMINI_API_KEYS` hoặc `GEMINI_API_KEY`. Thứ tự ưu tiên đã được nêu ở phần Cấu hình.
*   **Proxy:** `HTTP_PROXY` và `HTTPS_PROXY`. **Sẽ ghi đè** cài đặt proxy tĩnh trong file YAML hoặc `proxy_settings` khi khởi tạo `GeminiHandler` (trừ khi `proxy_settings` được truyền giá trị cụ thể).
*   **Server CLI:** Các biến như `GEMINI_HOST`, `GEMINI_PORT` có thể được dùng nếu không có tham số CLI tương ứng.

```bash
# API Keys (ưu tiên theo quy tắc đã nêu)
export GEMINI_API_KEYS="key1,key2,key3"
# export GEMINI_API_KEY="key-cua-ban"

# Proxy (sẽ ghi đè proxy tĩnh từ file config)
export HTTP_PROXY="http://proxy.server:port"
export HTTPS_PROXY="http://proxy.server:port"

# Cài đặt Server (nếu chạy CLI không có args)
# export GEMINI_HOST="127.0.0.1"
# export GEMINI_PORT="9000"
```

## 🚀 Ví dụ thực tế: Xây dựng Chatbot Bền bỉ

(Giữ nguyên ví dụ chatbot, nó đã sử dụng các chiến lược tốt)

## 🧩 Các Thành phần Chính

*   **`GeminiHandler`:** Class chính, quản lý cấu hình, key, chiến lược, proxy và gọi các API. Kế thừa từ `ContentGenerationMixin` và `FileOperationsMixin`.
*   **`ContentGenerationMixin`:** Chứa các phương thức tạo nội dung (`generate_content`, `generate_structured_content`, `generate_embeddings`).
*   **`FileOperationsMixin`:** Chứa các phương thức liên quan đến file (upload, get, list, delete, generate with file, generate with local file).
*   **`Strategy` (Enum):** Định nghĩa các chiến lược tạo nội dung.
*   **`KeyRotationStrategy` (Enum):** Định nghĩa các chiến lược luân chuyển API key.
*   **`GenerationConfig`:** Dataclass cấu hình tham số model.
*   **`EmbeddingConfig`:** Dataclass cho tham số embedding.
*   **`ModelResponse`:** Dataclass chuẩn hóa kết quả, bao gồm `success`, `text`, `structured_data`, `embeddings`, `error`, `time`, `api_key_index`, `file_info`, `proxy_info`.
*   **`KeyRotationManager`:** Xử lý logic chọn, theo dõi và luân chuyển API key.
*   **`FileHandler`:** Lớp cấp thấp xử lý tương tác Gemini File API.
*   **`EmbeddingHandler`:** Lớp xử lý gọi API embedding.
*   **`ResponseHandler`:** Xử lý và chuẩn hóa phản hồi thô từ API, kiểm tra lỗi, phân tích JSON.
*   **`strategies.py`:** Chứa các class triển khai `ContentStrategy`.
*   **`config.py` (`ConfigLoader`):** Tiện ích nạp API key và proxy tĩnh từ nhiều nguồn.
*   **`proxy.py` (`ProxyManager`):** Quản lý cấu hình proxy (tĩnh và tự động), áp dụng proxy cho môi trường.
*   **`auto_proxy.py` (`AutoProxyManager`):** (Phụ thuộc SwiftShadow) Quản lý việc lấy và cập nhật proxy tự động.
*   **`server.py` (`GeminiServer`):** Implement server FastAPI tương thích OpenAI, tích hợp middleware proxy.
*   **`cli.py`:** Giao diện dòng lệnh để khởi chạy `GeminiServer`.
*   **`litellm_integration.py` (`LiteLLMGeminiAdapter`):** Adapter tích hợp với LiteLLM.
*   **`config_loader.py` (`ServerConfig`):** (Ít dùng trực tiếp) Lớp cấu hình riêng cho server.

## 📄 Giấy phép

Dự án này được phát hành theo Giấy phép MIT - xem file `LICENSE` để biết thêm chi tiết.

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo Pull Request hoặc mở Issue.

