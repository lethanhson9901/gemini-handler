from pathlib import Path

from gemini_handler import GeminiHandler, GenerationConfig

# Define system prompt
system_instruction = """
Hãy chuyển đổi file scan PDF đính kèm thành định dạng markdown có cấu trúc tốt cho RAG. Yêu cầu cụ thể:

1. Trích xuất toàn bộ nội dung văn bản từ tất cả các trang PDF.

2. Định dạng cấu trúc rõ ràng:
   - Tiêu đề chính của tài liệu dùng # (một dấu thăng)
   - Tiêu đề chương dùng ## (hai dấu thăng)
   - Tiêu đề mục dùng ### (ba dấu thăng)
   - Tiêu đề mục nhỏ dùng #### (bốn dấu thăng)

3. Giữ nguyên thứ tự nội dung và cấu trúc phân cấp của tài liệu gốc.

4. Nếu có bất kỳ hình ảnh nào trong tài liệu, đánh dấu vị trí của chúng bằng: [Hình ảnh: mô tả ngắn gọn nếu có thể xác định].

5. Nếu có bảng biểu, hãy chuyển đổi thành định dạng bảng markdown.

6. Nếu có phần nào không thể đọc được hoặc không chắc chắn, hãy đánh dấu bằng [Không rõ nội dung].

7. KHÔNG THÊM nội dung không có trong tài liệu gốc.

8. Giữ nguyên tất cả số trang, số chương, số mục và các số tham chiếu khác.

Đây là một nhiệm vụ chuyển đổi thuần túy, chỉ dựa trên những gì thực sự có trong tài liệu PDF.
"""

# Create generation config with text/plain MIME type
generation_config = GenerationConfig(
    temperature=0.7,
    top_p=0.95,
    response_mime_type="text/plain"  # Set MIME type here
)

# Initialize handler with config file and system prompt
handler = GeminiHandler(
    config_path="../config.yaml",
    system_instruction=system_instruction,
    generation_config=generation_config  # Pass the generation config here
)

# Path to the PDF file
pdf_path = Path("1.pdf")

# Check if the file exists
if not pdf_path.exists():
    print(f"Không tìm thấy file PDF tại {pdf_path}")
else:
    # Upload file to Gemini API
    print("Đang tải PDF lên...")
    upload_result = handler.upload_file(pdf_path)
    
    if not upload_result['success']:
        print(f"Lỗi khi tải PDF: {upload_result['error']}")
    else:
        print(f"Đã tải PDF thành công với ID: {upload_result['name']}")
        
        # Analyze PDF
        print("Đang phân tích PDF...")
        analysis = handler.generate_content_with_file(
            file=upload_result['file'],
            prompt="Trích xuất toàn bộ nội dung từ file PDF và định dạng thành markdown rõ ràng, có cấu trúc."
        )
        
        # Display analysis results
        if analysis['success']:
            print("\nKết quả phân tích:")
            print(analysis['text'])
        else:
            print(f"Lỗi khi phân tích: {analysis['error']}")
        
        # Delete file after use
        print("\nĐang xóa file...")
        delete_result = handler.delete_file(upload_result['name'])
        if delete_result['success']:
            print("Đã xóa file thành công.")
        else:
            print(f"Lỗi khi xóa file: {delete_result['error']}")
