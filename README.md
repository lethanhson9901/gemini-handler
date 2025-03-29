# Gemini Handler

Thư viện Python giúp tương tác hiệu quả với API Gemini của Google, với các tính năng quản lý API key thông minh và xử lý phản hồi linh hoạt.

## Tính năng nổi bật

- **Quản lý nhiều API key**: Tự động luân chuyển, tối ưu hóa sử dụng và xử lý giới hạn tốc độ
- **Đa dạng chiến lược tạo nội dung**: Hỗ trợ nhiều phương pháp như luân phiên, dự phòng và thử lại
- **Hỗ trợ đầu ra có cấu trúc**: Tạo dữ liệu JSON theo schema tùy chỉnh
- **Xử lý lỗi thông minh**: Tự động thử lại và chuyển đổi phương án khi gặp lỗi
- **Theo dõi hiệu suất**: Giám sát việc sử dụng API và thời gian phản hồi

## Cài đặt

```bash
pip install gemini-handler
```

Hoặc cài đặt từ mã nguồn:

```bash
git clone https://github.com/yourusername/gemini-handler.git
cd gemini-handler
pip install -e .
```

## Hướng dẫn sử dụng cơ bản

### Tạo nội dung đơn giản

```python
from gemini_handler import GeminiHandler

# Khởi tạo handler với file cấu hình
handler = GeminiHandler(config_path="config.yaml")

# Tạo nội dung
response = handler.generate_content("Giải thích về trí tuệ nhân tạo cho người mới bắt đầu")

# Kiểm tra và hiển thị kết quả
if response['success']:
    print(response['text'])
else:
    print(f"Lỗi: {response['error']}")
```

### Tạo dữ liệu có cấu trúc

```python
# Định nghĩa cấu trúc dữ liệu mong muốn
movie_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Tên phim"},
        "director": {"type": "string", "description": "Đạo diễn"},
        "year": {"type": "integer", "description": "Năm phát hành"},
        "rating": {"type": "number", "description": "Điểm đánh giá"}
    },
    "required": ["title", "director", "year", "rating"]
}

# Tạo dữ liệu có cấu trúc
result = handler.generate_structured_content(
    prompt="Giới thiệu một bộ phim khoa học viễn tưởng hay",
    schema=movie_schema
)

# Hiển thị kết quả
if result['success']:
    movie = result['structured_data']
    print(f"Tên phim: {movie['title']}")
    print(f"Đạo diễn: {movie['director']}")
    print(f"Năm: {movie['year']}")
    print(f"Điểm đánh giá: {movie['rating']}")
```

## Cấu hình

Tạo file `config.yaml` với các thiết lập sau:

```yaml
gemini:
  # API Keys (bắt buộc)
  api_keys:
    - "api-key-1-của-bạn"
    - "api-key-2-của-bạn"

  # Cài đặt tạo nội dung (tùy chọn)
  generation:
    temperature: 0.7          # Độ sáng tạo (0.0-1.0)
    top_p: 1.0                # Ngưỡng lấy mẫu
    top_k: 40                 # Số lượng token xem xét
    max_output_tokens: 8192   # Độ dài tối đa của phản hồi

  # Giới hạn tốc độ (tùy chọn)
  rate_limits:
    requests_per_minute: 60   # Số request tối đa mỗi phút
    reset_window: 60          # Thời gian làm mới (giây)

  # Chiến lược (tùy chọn)
  strategies:
    content: "round_robin"    # Chiến lược tạo nội dung
    key_rotation: "smart_cooldown"  # Chiến lược luân chuyển key

  # Cài đặt thử lại (tùy chọn)
  retry:
    max_attempts: 3           # Số lần thử tối đa
    delay: 30                 # Thời gian chờ giữa các lần thử (giây)

  # Model mặc định (tùy chọn)
  default_model: "gemini-2.0-flash-exp"
```

## Các chiến lược

### Chiến lược tạo nội dung

| Chiến lược | Mô tả | Khi nào sử dụng |
|------------|-------|-----------------|
| **Round Robin** (Luân phiên) | Sử dụng lần lượt các model theo vòng tròn | Khi muốn phân tán tải đều cho các model |
| **Fallback** (Dự phòng) | Thử model theo thứ tự, chuyển sang model tiếp theo khi gặp lỗi | Khi cần độ tin cậy cao |
| **Retry** (Thử lại) | Thử lại cùng một model nhiều lần khi gặp lỗi | Khi muốn nhất quán về model sử dụng |

### Chiến lược luân chuyển API key

| Chiến lược | Mô tả | Khi nào sử dụng |
|------------|-------|-----------------|
| **Sequential** (Tuần tự) | Sử dụng các key theo thứ tự cố định | Khi muốn ưu tiên một số key nhất định |
| **Round Robin** (Luân phiên) | Sử dụng các key lần lượt theo vòng tròn | Khi muốn phân bổ đều các request |
| **Least Used** (Ít dùng nhất) | Ưu tiên key có số lần sử dụng ít nhất | Khi cần cân bằng tải giữa các key |
| **Smart Cooldown** (Làm mát thông minh) | Tự động điều chỉnh việc sử dụng key dựa trên lỗi | Khi cần khả năng tự phục hồi cao |

## Sử dụng nâng cao

### Tùy chỉnh chiến lược

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Khởi tạo với chiến lược tùy chỉnh
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK,         # Dùng chiến lược dự phòng
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN  # Dùng chiến lược làm mát thông minh
)
```

### Theo dõi hiệu suất

```python
# Tạo nội dung với thông tin hiệu suất
response = handler.generate_content(
    prompt="Viết một bài phân tích về xu hướng AI năm 2023",
    return_stats=True
)

# Hiển thị thông tin hiệu suất
print(f"Thời gian tạo: {response['time']} giây")
print(f"Model đã sử dụng: {response['model']}")
```

### Giám sát sử dụng API key

```python
# Lấy thống kê sử dụng key
key_stats = handler.get_key_stats()

# Hiển thị thông tin từng key
for key_idx, stats in key_stats.items():
    print(f"Key {key_idx}:")
    print(f"  Số lần sử dụng: {stats['uses']}")
    print(f"  Lần cuối sử dụng: {stats['last_used']}")
    print(f"  Số lần thất bại: {stats['failures']}")
```

## Xử lý lỗi

```python
# Tạo nội dung với xử lý lỗi
response = handler.generate_content("Prompt của bạn")

# Kiểm tra kết quả
if response['success']:
    print(response['text'])
else:
    print(f"Lỗi: {response['error']}")
    print(f"Số lần thử: {response['attempts']}")
    print(f"Model đã thử: {response['model']}")
```

## Sử dụng biến môi trường

Bạn cũng có thể cấu hình thông qua biến môi trường:

```bash
# Nhiều key
export GEMINI_API_KEYS="key1,key2,key3"

# Một key
export GEMINI_API_KEY="key-của-bạn"

# Cài đặt khác
export GEMINI_DEFAULT_MODEL="gemini-2.0-flash-exp"
export GEMINI_MAX_RETRIES="3"
```

## Ví dụ thực tế

### Xây dựng chatbot với xử lý lỗi mạnh mẽ

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Khởi tạo handler với chiến lược tối ưu
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)

def chat_with_user():
    print("Chatbot: Xin chào! Tôi có thể giúp gì cho bạn?")
    
    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["tạm biệt", "bye", "exit"]:
            print("Chatbot: Tạm biệt! Hẹn gặp lại!")
            break
            
        # Tạo phản hồi với xử lý lỗi
        response = handler.generate_content(
            prompt=f"User: {user_input}\nChatbot:",
            model_name="gemini-2.0-flash-exp"
        )
        
        if response['success']:
            print(f"Chatbot: {response['text']}")
        else:
            # Thử lại với model khác nếu gặp lỗi
            fallback_response = handler.generate_content(
                prompt=f"User: {user_input}\nChatbot:",
                model_name="gemini-1.5-flash"
            )
            
            if fallback_response['success']:
                print(f"Chatbot: {fallback_response['text']}")
            else:
                print("Chatbot: Xin lỗi, tôi đang gặp vấn đề kỹ thuật. Vui lòng thử lại sau.")

# Chạy chatbot
if __name__ == "__main__":
    chat_with_user()
```

## Tạo Embedding

Thư viện hỗ trợ tạo embedding từ văn bản để sử dụng trong các ứng dụng tìm kiếm ngữ nghĩa, phân loại, và nhiều tác vụ khác.

### Tạo Embedding Cơ Bản

```python
from gemini_handler import GeminiHandler

handler = GeminiHandler(config_path="config.yaml")

# Tạo embedding cho một đoạn văn bản
result = handler.generate_embeddings(content="Trí tuệ nhân tạo là gì?")

# Kiểm tra kết quả
if result['success']:
    embeddings = result['embeddings']
    print(f"Đã tạo embedding {len(embeddings)} chiều")
    print(f"Các chiều đầu tiên: {embeddings[:5]}")
else:
    print(f"Lỗi: {result['error']}")


## Giấy phép

Dự án này được phát hành theo Giấy phép MIT - xem file LICENSE để biết thêm chi tiết.

## Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo Pull Request hoặc mở Issue nếu bạn có ý tưởng cải tiến.