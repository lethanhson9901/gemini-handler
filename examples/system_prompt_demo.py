from pathlib import Path

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

# Đường dẫn đến file hình ảnh
image_path = Path("1.png")

# Kiểm tra xem file có tồn tại không
if not image_path.exists():
    print(f"Không tìm thấy file hình ảnh tại {image_path}")
else:
    # Upload file lên Gemini API
    print("Đang tải hình ảnh lên...")
    upload_result = handler.upload_file(image_path)
    
    if not upload_result['success']:
        print(f"Lỗi khi tải hình ảnh: {upload_result['error']}")
    else:
        print(f"Đã tải hình ảnh thành công với ID: {upload_result['name']}")
        
        # Phân tích hình ảnh
        print("Đang phân tích hình ảnh...")
        analysis = handler.generate_content_with_file(
            file=upload_result['file'],
            prompt="Mô tả chi tiết những gì bạn thấy trong hình ảnh này."
        )
        
        # Hiển thị kết quả phân tích
        if analysis['success']:
            print("\nKết quả phân tích:")
            print(analysis['text'])
        else:
            print(f"Lỗi khi phân tích: {analysis['error']}")
        
        # Xóa file sau khi sử dụng
        print("\nĐang xóa file...")
        handler.delete_file(upload_result['name'])
        print("Đã xóa file thành công.")
