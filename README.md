Okay, let's integrate the detailed information from the English README into your existing Vietnamese README, enriching it with more features and examples.

```markdown
# Gemini Handler 🚀

[![Giấy phép: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Cập nhật nếu giấy phép khác -->
[![Trạng thái Build](https://img.shields.io/travis/com/your-username/gemini-handler.svg)](https://travis-ci.com/your-username/gemini-handler) <!-- Liên kết đến CI/CD của bạn -->

**Thư viện Python mạnh mẽ giúp tương tác hiệu quả với API Gemini của Google, tích hợp các tính năng quản lý API key thông minh, chiến lược xử lý lỗi linh hoạt, khả năng xử lý file và tạo đầu ra có cấu trúc.**

`gemini-handler` đơn giản hóa các tác vụ phổ biến và tăng cường độ bền cho các ứng dụng sử dụng Gemini của bạn. Thư viện quản lý thông minh nhiều API key để giảm thiểu giới hạn tốc độ (rate limit), cung cấp nhiều chiến lược xử lý lỗi API, và các phương thức tiện lợi cho việc tạo văn bản, tạo embedding, thao tác file và tạo dữ liệu có cấu trúc (JSON).

## ✨ Tính năng nổi bật

*   **🤖 Hỗ trợ nhiều Model Gemini:** Tương tác với các model Gemini khác nhau cho tác vụ văn bản và hình ảnh (vision).
*   **🔑 Quản lý API Key Nâng cao:**
    *   Nạp key từ biến môi trường (`GEMINI_API_KEY`, `GEMINI_API_KEYS`) hoặc file cấu hình YAML.
    *   Nhiều chiến lược luân chuyển key (`ROUND_ROBIN`, `SEQUENTIAL`, `LEAST_USED`, `SMART_COOLDOWN`) để phân phối tải và xử lý rate limit một cách mượt mà.
    *   Tự động "làm mát" (cooldown) cho các key bị giới hạn tốc độ.
    *   Theo dõi thống kê sử dụng key (số lần dùng, lỗi, thời gian bị giới hạn).
*   **🔄 Tạo Nội dung Bền bỉ:**
    *   **Chiến lược Retry (Thử lại):** Tự động thử lại các yêu cầu thất bại với độ trễ có thể cấu hình.
    *   **Chiến lược Fallback (Dự phòng):** Thử tạo nội dung với một chuỗi các model nếu model chính thất bại.
    *   **Chiến lược Round Robin (Luân phiên):** Lần lượt thử qua các model có sẵn.
*   **📄 Đầu ra có cấu trúc (JSON):** Tạo nội dung tuân thủ nghiêm ngặt theo một JSON schema được cung cấp.
*   **🖼️ Xử lý File:**
    *   Tải file cục bộ lên API Gemini.
    *   Quản lý các file đã tải lên (lấy thông tin, liệt kê, xóa).
    *   Tải hàng loạt file từ một thư mục.
*   **👁️ Khả năng Vision:**
    *   Tạo nội dung dựa trên hình ảnh/file đã tải lên.
    *   Tạo nội dung trực tiếp từ file hình ảnh cục bộ mà không cần tải lên trước.
*   **💡 Tạo Embedding:** Tạo embedding văn bản sử dụng các model embedding Gemini được chỉ định.
*   **⚙️ Tùy chỉnh Linh hoạt:** Cấu hình các tham số tạo nội dung (temperature, top_p, v.v.) và system instructions.
*   **📊 Phản hồi Chuẩn hóa:** Đối tượng `ModelResponse` nhất quán cho mọi kết quả, bao gồm trạng thái thành công, văn bản/dữ liệu, lỗi, thời gian xử lý và thông tin key đã sử dụng.

## 🛠️ Cài đặt

Đảm bảo bạn đã cài đặt các thư viện cơ bản:
```bash
pip install google-generativeai PyYAML
```

Cài đặt `gemini-handler`:
```bash
# Giả sử thư viện có thể cài đặt qua pip (khi được xuất bản)
# pip install gemini-handler

# Hoặc cài đặt từ mã nguồn cục bộ:
# git clone https://github.com/your-username/gemini-handler.git # Thay bằng đường dẫn repo của bạn
# cd gemini-handler
# pip install .
```

*(Lưu ý: Thay thế `your-username/gemini-handler` bằng đường dẫn kho lưu trữ thực tế của bạn nếu có)*

## 🔑 Cấu hình: API Keys

`gemini-handler` cần các API key Google Gemini của bạn. Thư viện sẽ nạp key theo thứ tự ưu tiên sau:

1.  **Danh sách key truyền trực tiếp (Code):** Cung cấp `api_keys=['key1', 'key2']` khi khởi tạo `GeminiHandler`.
2.  **File Cấu hình YAML:** Cung cấp `config_path="duong/dan/toi/config.yaml"` khi khởi tạo. File YAML cần có cấu trúc:
    ```yaml
    # config.yaml
    gemini:
      api_keys:
        - "API_KEY_CUA_BAN_1"
        - "API_KEY_CUA_BAN_2"
        # - "..." Thêm các key khác nếu cần
    ```
3.  **Biến Môi trường (Nhiều Keys):** Đặt biến `GEMINI_API_KEYS` là một chuỗi các key, phân tách bởi dấu phẩy:
    ```bash
    export GEMINI_API_KEYS="API_KEY_CUA_BAN_1,API_KEY_CUA_BAN_2,API_KEY_CUA_BAN_3"
    ```
4.  **Biến Môi trường (Một Key):** Đặt biến `GEMINI_API_KEY`:
    ```bash
    export GEMINI_API_KEY="API_KEY_DUY_NHAT_CUA_BAN"
    ```

Nếu không tìm thấy key nào qua các phương thức trên, thư viện sẽ báo lỗi `ValueError`.

**(Phần Cấu hình YAML Chi tiết)**

Bạn có thể tùy chỉnh sâu hơn trong file `config.yaml`:

```yaml
gemini:
  # API Keys (bắt buộc)
  api_keys:
    - "api-key-1-của-bạn"
    - "api-key-2-của-bạn"
    # - "..."

  # Cài đặt tạo nội dung (tùy chọn) - Sẽ được dùng nếu không override khi gọi hàm
  generation:
    temperature: 0.7          # Độ sáng tạo (0.0-1.0)
    top_p: 1.0                # Ngưỡng xác suất tích lũy
    top_k: 40                 # Số lượng token có xác suất cao nhất để xem xét
    max_output_tokens: 8192   # Độ dài tối đa của phản hồi (tính bằng token)
    # stop_sequences: ["\n", "Ví dụ:"] # Danh sách các chuỗi dừng tạo nội dung

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
  default_model: "gemini-1.5-flash" # Model dùng khi không chỉ định trong hàm gọi
  default_embedding_model: "gemini-embedding-exp-03-07" # Model embedding mặc định
```

## 🚀 Hướng dẫn sử dụng

### 1. Khởi tạo Cơ bản

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy, GenerationConfig

# Khởi tạo đơn giản nhất (nạp key từ ENV hoặc config.yaml mặc định nếu có)
handler_default = GeminiHandler()

# Khởi tạo với danh sách key và chiến lược cụ thể
api_keys = ["API_KEY_CUA_BAN_1", "API_KEY_CUA_BAN_2"]
handler_custom = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.RETRY,       # Dùng chiến lược Retry
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN # Dùng Smart Cooldown cho key
)

# Khởi tạo với file cấu hình và system instruction
system_instruction = "Bạn là một trợ lý AI hữu ích."
handler_with_config = GeminiHandler(
    config_path="config.yaml",
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
system_instruction = """
Bạn là một trợ lý giáo dục chuyên về giải thích các khái niệm phức tạp cho người mới bắt đầu.
Khi giải thích, hãy tuân theo các nguyên tắc sau:
- Sử dụng ngôn ngữ đơn giản, tránh thuật ngữ chuyên ngành khi có thể
- Luôn bắt đầu với định nghĩa cơ bản, sau đó mới đi vào chi tiết
- Đưa ra ví dụ thực tế mà người bình thường có thể liên hệ được
- Chia thông tin thành các phần nhỏ, dễ hiểu
- Kết thúc bằng một tóm tắt ngắn gọn về những điểm chính
"""
# handler.system_instruction = system_instruction # Có thể gán lại nếu cần

prompt = "Giải thích về trí tuệ nhân tạo cho người mới bắt đầu."
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
    prompt="Viết một bài thơ ngắn về mặt trăng.",
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
movie_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Tên phim"},
        "director": {"type": "string", "description": "Đạo diễn"},
        "year": {"type": "integer", "description": "Năm phát hành"},
        "genres": {"type": "array", "items": {"type": "string"}, "description": "Thể loại phim"},
        "rating": {"type": "number", "description": "Điểm đánh giá (thang 10)"}
    },
    "required": ["title", "director", "year", "genres", "rating"]
}

prompt = "Giới thiệu một bộ phim khoa học viễn tưởng nổi tiếng của Christopher Nolan, bao gồm tên, đạo diễn, năm phát hành, thể loại và điểm đánh giá."

# Tạo dữ liệu có cấu trúc
result = handler.generate_structured_content(
    prompt=prompt,
    schema=movie_schema,
    model_name="gemini-1.5-pro" # Nên dùng model mạnh hơn cho JSON phức tạp
    # temperature=0.2 # Có thể override tham số generation ở đây
)

if result['success'] and result['structured_data']:
    print("\nDữ liệu cấu trúc được tạo:")
    movie = result['structured_data']
    print(json.dumps(movie, indent=2, ensure_ascii=False)) # ensure_ascii=False để hiển thị tiếng Việt
    # print(f"\nVăn bản gốc từ API: {result['text']}") # Có thể hữu ích để debug
else:
    print(f"\nLỗi khi tạo dữ liệu cấu trúc: {result['error']}")
    if not result['structured_data'] and result['success']:
        print(f"Không thể phân tích JSON từ văn bản trả về: {result['text']}")
```

### 4. Tạo Embedding

```python
from gemini_handler import EmbeddingConfig # Import để dùng hằng số task_type

# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

content_to_embed = [
    "Thời tiết hôm nay thế nào?",
    "Cách làm bánh mì?",
    "Lịch sử Việt Nam tóm tắt",
]

# Tạo embedding đơn giản
response = handler.generate_embeddings(content=content_to_embed)

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
    task_type=EmbeddingConfig.RETRIEVAL_DOCUMENT, # Chỉ định loại tác vụ
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

# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

# --- Tải File Lên ---
file_path = "duong/dan/toi/hinh_anh_cua_ban.jpg" # Hoặc file PDF, video, audio... được hỗ trợ
# Đảm bảo file tồn tại trước khi tải
if not Path(file_path).exists():
     print(f"Lỗi: File không tồn tại tại {file_path}")
     # Xử lý lỗi hoặc thoát
else:
    print(f"Đang tải lên file: {file_path}...")
    upload_result = handler.upload_file(file_path)

    if upload_result['success']:
        uploaded_file_object = upload_result['file'] # Lấy đối tượng file gốc
        uploaded_file_name = uploaded_file_object.name # Lấy tên file dạng "files/..."
        print(f"File tải lên thành công: {uploaded_file_name}")
        print(f"URI: {uploaded_file_object.uri}")
        print(f"Trạng thái ban đầu: {uploaded_file_object.state}")

        # Chờ file được xử lý (quan trọng!)
        print("Đang chờ file xử lý...")
        while uploaded_file_object.state.name == "PROCESSING":
            time.sleep(5) # Đợi 5 giây
            get_result = handler.get_file(uploaded_file_name)
            if get_result['success']:
                uploaded_file_object = get_result['file']
            else:
                print(f"Lỗi khi kiểm tra trạng thái file: {get_result['error']}")
                break # Thoát vòng lặp nếu không kiểm tra được

        if uploaded_file_object.state.name == "ACTIVE":
            print("File đã sẵn sàng để sử dụng.")

            # --- Lấy Thông tin File ---
            get_result = handler.get_file(uploaded_file_name)
            if get_result['success']:
                print(f"\nThông tin file: {get_result['name']}")
                print(f"  Trạng thái: {get_result['state']}")
                print(f"  Loại MIME: {get_result['mime_type']}")
                print(f"  Kích thước: {get_result['size_bytes']} bytes")

            # --- Tạo Nội dung với File Đã Tải Lên (Văn bản) ---
            prompt_cho_file = "Mô tả chi tiết nội dung của hình ảnh này."
            # Sử dụng tên file hoặc đối tượng file đã lấy được
            file_gen_response = handler.generate_content_with_file(
                file=uploaded_file_name, # Hoặc file=uploaded_file_object
                prompt=prompt_cho_file,
                model_name="gemini-1.5-pro" # Bắt buộc dùng model vision
            )
            if file_gen_response['success']:
                print("\nNội dung được tạo từ File:")
                print(file_gen_response['text'])
            else:
                print(f"\nLỗi khi tạo nội dung từ file: {file_gen_response['error']}")

            # --- Tạo Nội dung với File Đã Tải Lên (JSON) ---
            image_schema = {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Mô tả ngắn gọn về ảnh"},
                    "objects_detected": {"type": "array", "items": {"type": "string"}, "description": "Danh sách các đối tượng chính phát hiện được"},
                    "dominant_colors": {"type": "array", "items": {"type": "string"}, "description": "Các màu sắc chủ đạo"}
                },
                "required": ["description", "objects_detected"]
            }
            structured_file_gen_response = handler.generate_structured_content_with_file(
                 file=uploaded_file_name,
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
            print(f"File không ở trạng thái ACTIVE (trạng thái hiện tại: {uploaded_file_object.state.name}). Không thể sử dụng.")
            # Cân nhắc xóa file nếu xử lý lỗi
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
            print(f" - {f['name']} ({f['mime_type']}, Trạng thái: {f['state']})")
        if list_result['next_page_token']:
            print(f"Còn trang tiếp theo (next_page_token): {list_result['next_page_token']}")
    else:
        print("  (Không có file nào)")
else:
    print(f"Lỗi khi liệt kê files: {list_result['error']}")

# --- Tải Hàng Loạt (Batch Upload) ---
# Tạo thư mục và file giả để ví dụ
Path("temp_upload_dir").mkdir(exist_ok=True)
Path("temp_upload_dir/tai_lieu_1.txt").write_text("Nội dung file text 1.")
Path("temp_upload_dir/hinh_anh.png").touch() # Tạo file rỗng
Path("temp_upload_dir/script.py").write_text("print('Hello')")

print("\nĐang tải lên hàng loạt từ thư mục 'temp_upload_dir'...")
batch_result = handler.batch_upload_files(
    directory_path="temp_upload_dir",
    file_extensions=['.txt', '.png'] # Tùy chọn: chỉ tải file có đuôi .txt hoặc .png
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
    shutil.rmtree("temp_upload_dir")
    print("Đã xóa thư mục tạm 'temp_upload_dir'.")
except OSError as e:
    print(f"Lỗi khi xóa thư mục tạm: {e}")

```

### 6. Tạo Nội dung với File Cục bộ (Không cần Upload)

Hữu ích cho việc phân tích nhanh hình ảnh cục bộ mà không cần lưu trữ chúng qua File API.

```python
# handler = GeminiHandler(...) # Đảm bảo bạn đã có instance handler

local_image_path = "duong/dan/toi/hinh_anh_cuc_bo.jpeg"

if not Path(local_image_path).exists():
    print(f"Lỗi: File cục bộ không tồn tại: {local_image_path}")
else:
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
        prompt="Mô tả chủ thể chính và hậu cảnh của bức ảnh này.",
        schema={ # Ví dụ schema đơn giản
            "type": "object",
            "properties": {
                "chu_the_chinh": {"type": "string"},
                "hau_canh": {"type": "string"}
            },
            "required": ["chu_the_chinh", "hau_canh"]
        },
        model_name="gemini-1.5-pro" # Dùng model vision hỗ trợ JSON
    )

    if local_structured_response['success'] and local_structured_response['structured_data']:
        print("\nDữ liệu cấu trúc được tạo từ File Cục bộ:")
        print(json.dumps(local_structured_response['structured_data'], indent=2, ensure_ascii=False))
    else:
        print(f"\nLỗi khi tạo dữ liệu cấu trúc từ file cục bộ: {local_structured_response['error']}")
```

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
| **`ROUND_ROBIN`**      | Sử dụng các key lần lượt theo vòng tròn, bỏ qua key bị rate limit.                                     | Khi muốn phân bổ đều các request, dễ dự đoán.          |
| **`LEAST_USED`**       | Ưu tiên key có số lần sử dụng ít nhất trong khoảng `reset_window`.                                     | Khi cần cân bằng tải thực tế giữa các key.               |
| **`SMART_COOLDOWN`**   | Tự động "làm mát" key bị rate limit, ưu tiên key ít lỗi và đã nghỉ lâu nhất trong số key khả dụng.   | Khi cần khả năng tự phục hồi cao, tối ưu khi key bị limit. |

## 💡 Sử dụng nâng cao

### Tùy chỉnh chiến lược khi khởi tạo

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Khởi tạo với chiến lược tùy chỉnh
handler_advanced = GeminiHandler(
    config_path="config.yaml", # Hoặc api_keys=[...]
    content_strategy=Strategy.FALLBACK,         # Dùng chiến lược dự phòng
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN, # Dùng chiến lược làm mát thông minh
    # Có thể override các cài đặt khác từ config.yaml ở đây
    # generation_config=GenerationConfig(temperature=0.8)
)
# Sử dụng handler_advanced cho các tác vụ tiếp theo
```

### Theo dõi hiệu suất Request

```python
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
    # Chuyển đổi timestamp sang dạng đọc được
    import datetime
    last_used_time = datetime.datetime.fromtimestamp(stats['last_used']).strftime('%Y-%m-%d %H:%M:%S') if stats['last_used'] > 0 else "Chưa sử dụng"
    print(f"    Lần cuối sử dụng: {last_used_time}")
    print(f"    Số lần thất bại liên tiếp: {stats['failures']}")
    rate_limited_until_time = datetime.datetime.fromtimestamp(stats['rate_limited_until']).strftime('%Y-%m-%d %H:%M:%S') if stats['rate_limited_until'] > time.time() else "Không bị giới hạn"
    print(f"    Bị giới hạn đến: {rate_limited_until_time}")

```

## ⚠️ Xử lý lỗi

Thư viện được thiết kế để xử lý lỗi một cách linh hoạt thông qua các chiến lược. Tuy nhiên, bạn vẫn cần kiểm tra kết quả trả về.

*   Luôn kiểm tra giá trị `response['success']` (boolean).
*   Nếu `success` là `False`, kiểm tra `response['error']` để biết chi tiết lỗi.
*   `response['model']` cho biết model cuối cùng được thử (có thể là model gây lỗi hoặc model fallback).
*   `response['attempts']` (chỉ có ý nghĩa với chiến lược `RETRY`) cho biết số lần đã thử.
*   Thư viện tự động xử lý lỗi rate limit (`429`) bằng cách chuyển key hoặc làm mát key (tùy thuộc `key_strategy`).
*   Các phản hồi bị chặn do vi phạm bản quyền (finish reason 4) cũng được coi là lỗi và ghi vào `response['error']`.

```python
# Ví dụ xử lý lỗi rõ ràng hơn
response = handler.generate_content("Một prompt có thể gây lỗi hoặc bị chặn")

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
    # Có thể thêm logic xử lý lỗi ở đây, ví dụ: log lỗi, thông báo cho người dùng,...
```

## ⚙️ Sử dụng Biến Môi trường (Ngoài file YAML)

Bạn cũng có thể cấu hình một số tham số chính thông qua biến môi trường (sẽ ghi đè giá trị trong file YAML nếu cả hai cùng tồn tại, trừ `api_keys` sẽ được ưu tiên theo thứ tự đã nêu):

```bash
# API Keys (ưu tiên cao hơn YAML nếu được đặt)
export GEMINI_API_KEYS="key1,key2,key3"
# export GEMINI_API_KEY="key-cua-ban" # Chỉ dùng nếu GEMINI_API_KEYS không có

# Cài đặt khác (sẽ ghi đè giá trị tương ứng trong YAML)
export GEMINI_DEFAULT_MODEL="gemini-1.5-pro"
export GEMINI_MAX_RETRIES="5" # Số lần thử lại tối đa cho Retry Strategy
export GEMINI_RETRY_DELAY="45" # Thời gian chờ giữa các lần thử lại (giây)
# Lưu ý: Các chiến lược và cấu hình generation phức tạp hơn nên đặt trong YAML
```

## 🚀 Ví dụ thực tế: Xây dựng Chatbot Bền bỉ

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy
import sys

# Khởi tạo handler với chiến lược tối ưu cho chatbot
try:
    chatbot_handler = GeminiHandler(
        config_path="config.yaml", # Đảm bảo file này tồn tại và có key
        content_strategy=Strategy.FALLBACK, # Ưu tiên model tốt, fallback nếu lỗi
        key_strategy=KeyRotationStrategy.SMART_COOLDOWN, # Xử lý rate limit tốt
        system_instruction="Bạn là một trợ lý ảo thân thiện và hữu ích tên là GemiBot."
    )
    print("GemiBot: Đã khởi tạo thành công!")
except ValueError as e:
    print(f"Lỗi khởi tạo GeminiHandler: {e}")
    print("Vui lòng kiểm tra cấu hình API key trong config.yaml hoặc biến môi trường.")
    sys.exit(1) # Thoát nếu không có key


def chat_with_user():
    print("\nGemiBot: Xin chào! Tôi có thể giúp gì cho bạn? (Gõ 'tạm biệt' để thoát)")
    conversation_history = []

    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["tạm biệt", "bye", "exit", "quit"]:
            print("GemiBot: Tạm biệt! Hẹn gặp lại!")
            break

        # Thêm vào lịch sử (đơn giản, có thể cải tiến)
        conversation_history.append(f"Bạn: {user_input}")

        # Tạo prompt với ngữ cảnh
        prompt = "\n".join(conversation_history) + "\nGemiBot:"

        # Tạo phản hồi với xử lý lỗi tích hợp
        # Ưu tiên dùng model mạnh hơn trước
        response = chatbot_handler.generate_content(
            prompt=prompt,
            model_name="gemini-1.5-pro" # Thử model mạnh trước
        )

        # Nếu model mạnh lỗi, thử model nhanh hơn (Fallback tự động nếu strategy là FALLBACK)
        # Nếu strategy không phải FALLBACK, cần tự xử lý fallback ở đây
        if not response['success'] and chatbot_handler._strategy.__class__.__name__ != "FallbackStrategy":
             print("GemiBot: (Đang thử model dự phòng...)")
             response = chatbot_handler.generate_content(
                 prompt=prompt,
                 model_name="gemini-1.5-flash" # Thử model nhanh hơn
             )

        # Hiển thị kết quả hoặc thông báo lỗi cuối cùng
        if response['success']:
            bot_reply = response['text'].strip()
            print(f"GemiBot: {bot_reply}")
            conversation_history.append(f"GemiBot: {bot_reply}")
        else:
            error_msg = response['error']
            print(f"GemiBot: Xin lỗi, tôi đang gặp chút vấn đề kỹ thuật ({error_msg}). Vui lòng thử lại sau giây lát.")
            # Xóa lượt hỏi lỗi khỏi lịch sử để tránh lặp lại lỗi
            conversation_history.pop()

        # Giới hạn lịch sử để tránh prompt quá dài (ví dụ: giữ 10 lượt thoại gần nhất)
        if len(conversation_history) > 20:
             conversation_history = conversation_history[-20:]


# Chạy chatbot
if __name__ == "__main__":
    chat_with_user()

```

## 🧩 Các Thành phần Chính

*   **`GeminiHandler`:** Điểm truy cập chính cho mọi tương tác. Điều phối quản lý key, chiến lược, và gọi API.
*   **`Strategy` (Enum):** Định nghĩa các chiến lược tạo nội dung (`ROUND_ROBIN`, `FALLBACK`, `RETRY`).
*   **`KeyRotationStrategy` (Enum):** Định nghĩa các chiến lược luân chuyển API key (`SEQUENTIAL`, `ROUND_ROBIN`, `LEAST_USED`, `SMART_COOLDOWN`).
*   **`GenerationConfig`:** Dataclass để cấu hình tham số model như `temperature`, `top_p`, `max_output_tokens`, `response_mime_type`, `response_schema`.
*   **`EmbeddingConfig`:** Dataclass cho tham số embedding, bao gồm `task_type`.
*   **`ModelResponse`:** Dataclass chuẩn hóa cho kết quả gọi API, chứa `success` (bool), `model` (str), `text` (str), `structured_data` (dict), `embeddings` (list), `error` (str), `time` (float), `api_key_index` (int), `file_info` (dict).
*   **`KeyRotationManager`:** Xử lý logic chọn và theo dõi API key.
*   **`FileHandler`:** Lớp cấp thấp hơn chuyên xử lý tương tác với Gemini File API (được `GeminiHandler` sử dụng nội bộ).
*   **`ConfigLoader`:** Tiện ích nạp API key từ nhiều nguồn.
*   **Mixins (`ContentGenerationMixin`, `FileOperationsMixin`):** Tổ chức các phương thức trong `GeminiHandler`.

## 📄 Giấy phép

Dự án này được phát hành theo Giấy phép MIT - xem file `LICENSE` để biết thêm chi tiết. (Tạo file LICENSE nếu chưa có).

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
```