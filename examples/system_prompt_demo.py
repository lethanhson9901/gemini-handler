from gemini_handler import GeminiHandler

# Định nghĩa system prompt
system_instruction = """
Bạn là một trợ lý giáo dục chuyên về giải thích các khái niệm phức tạp cho người mới bắt đầu.
Khi giải thích, hãy tuân theo các nguyên tắc sau:
- Sử dụng ngôn ngữ đơn giản, tránh thuật ngữ chuyên ngành khi có thể
- Luôn bắt đầu với định nghĩa cơ bản, sau đó mới đi vào chi tiết
- Đưa ra ví dụ thực tế mà người bình thường có thể liên hệ được
- Chia thông tin thành các phần nhỏ, dễ hiểu
- Kết thúc bằng một tóm tắt ngắn gọn về những điểm chính
"""

# Khởi tạo handler với file cấu hình và system prompt
handler = GeminiHandler(
    config_path="../config.yaml",
    system_instruction=system_instruction
)

# Tạo nội dung
response = handler.generate_content("Giải thích về trí tuệ nhân tạo cho người mới bắt đầu")

# Kiểm tra và hiển thị kết quả
if response['success']:
    print(response['text'])
else:
    print(f"Lỗi: {response['error']}")