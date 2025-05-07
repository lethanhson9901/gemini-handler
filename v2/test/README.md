# Gemini API Gateway: Tăng Cường Độ Tin Cậy và Khả Năng Mở Rộng

**Phiên bản:** 1.3.1

## Tổng Quan

Gemini API Gateway là một ứng dụng FastAPI được thiết kế để tối ưu hóa việc tương tác với Google Gemini API. Gateway này hoạt động như một lớp trung gian thông minh, cung cấp các tính năng quản lý proxy nâng cao, kiểm tra sức khỏe tự động, cơ chế thử lại linh hoạt và bảo mật truy cập, nhằm đảm bảo tính ổn định và hiệu suất cao cho các ứng dụng sử dụng Gemini.

## Tính Năng Nổi Bật

*   **Chuyển Tiếp Yêu Cầu An Toàn:** Định tuyến các yêu cầu API đến Gemini một cách bảo mật, tự động quản lý khóa API Gemini.
*   **Quản Lý Proxy Động:** Tích hợp với `swiftshadow` để thu thập và quản lý danh sách proxy.
*   **Kiểm Tra Sức Khỏe Proxy Chuyên Sâu:**
    *   Tự động xác minh tính khả dụng và hiệu suất của proxy bằng cách thực hiện các lệnh gọi kiểm tra đến một endpoint Gemini cụ thể.
    *   Chỉ những proxy vượt qua kiểm tra mới được đưa vào danh sách hoạt động (whitelist).
    *   Định kỳ kiểm tra lại các proxy trong whitelist và loại bỏ những proxy không còn đáp ứng.
*   **Danh Sách Trắng Proxy (Whitelist):** Ưu tiên sử dụng các proxy đã được kiểm chứng để tối đa hóa tỷ lệ thành công của yêu cầu.
*   **Cơ Chế Thử Lại (Retry) Thông Minh:**
    *   Tự động thử lại yêu cầu qua một proxy khác nếu gặp lỗi mạng hoặc proxy.
    *   Hỗ trợ cấu hình số lần thử lại và thời gian trễ giữa các lần thử.
*   **Dự Phòng Kết Nối Trực Tiếp:** Tùy chọn chuyển sang kết nối trực tiếp đến Gemini API nếu tất cả các nỗ lực qua proxy đều thất bại.
*   **Xoay Vòng Khóa API Gemini:** Phân phối yêu cầu qua nhiều khóa API Gemini để tránh giới hạn rate-limit và tăng khả năng phục hồi.
*   **Bảo Mật Gateway:** Truy cập vào gateway được kiểm soát thông qua một khóa API riêng biệt.
*   **Cấu Hình Tập Trung:** Quản lý toàn bộ cài đặt qua tệp `config.yaml` dễ hiểu.
*   **Logging Chi Tiết:** Ghi lại hoạt động và lỗi để hỗ trợ giám sát và gỡ rối.
*   **Endpoint Giám Sát Trạng Thái:** Cung cấp endpoint `/_gateway/health` để theo dõi tình trạng hoạt động của gateway.

## Yêu Cầu Hệ Thống

*   Python 3.8+
*   `pip` (Trình quản lý gói Python)

## Hướng Dẫn Cài Đặt

1.  **Tải Mã Nguồn:**
    Sao chép (clone) repository hoặc tải tệp mã nguồn chính (ví dụ: `gemini_gateway.py`).

2.  **Cài Đặt Thư Viện Phụ Thuộc:**
    Tạo tệp `requirements.txt` với nội dung sau:
    ```txt
    fastapi
    uvicorn[standard]
    httpx
    PyYAML
    swiftshadow
    ```
    Sau đó, chạy lệnh sau trong terminal tại thư mục dự án:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Thiết Lập Tệp Cấu Hình (`config.yaml`):**
    Tạo tệp `config.yaml` trong thư mục gốc của dự án. Tham khảo mục **Cấu Hình** bên dưới.

## Cấu Hình (`config.yaml`)

Tệp `config.yaml` cho phép tùy chỉnh các khía cạnh hoạt động của gateway.

**Ví dụ cấu hình cơ bản:**

```yaml
server_settings:
  host: "0.0.0.0"
  port: 8000
  server_key: "YOUR_SECURE_GATEWAY_KEY" # Thay thế bằng khóa API mạnh cho gateway

gemini:
  api_keys:
    - "YOUR_GEMINI_API_KEY_1"         # Thay thế bằng khóa API Gemini của bạn
    - "YOUR_GEMINI_API_KEY_2"         # (Tùy chọn) Thêm khóa khác để xoay vòng
  base_url: "https://generativelanguage.googleapis.com"

proxy_settings:
  auto_update_interval_seconds: 300
  max_proxies: 50 # Số lượng proxy tối đa swiftshadow quản lý

retry_settings:
  max_request_retries: 2
  fallback_to_direct_on_failure: true
  retry_delay_seconds: 1

health_check_settings:
  enabled: true
  health_check_api_key: "GEMINI_API_KEY_FOR_HEALTH_CHECKS" # KHUYẾN NGHỊ: Dùng khóa riêng
  health_check_model_endpoint: "v1beta/models/gemini-1.5-flash-latest" # Endpoint kiểm tra
  timeout_seconds: 10
  max_concurrent_checks: 5
  proxy_recheck_interval_seconds: 300
```

**Các tham số quan trọng:**

*   `server_settings.server_key`: Khóa API bí mật để xác thực các yêu cầu đến gateway.
*   `gemini.api_keys`: Danh sách các khóa API Google Gemini. Ít nhất một khóa là bắt buộc.
*   `health_check_settings.enabled`: Bật/tắt tính năng kiểm tra sức khỏe proxy.
*   `health_check_settings.health_check_api_key`: **Khuyến nghị mạnh mẽ** sử dụng một khóa API Gemini riêng cho việc kiểm tra sức khỏe để tránh ảnh hưởng đến quota của các khóa chính.

## Khởi Chạy Gateway

Thực thi tệp Python chính từ terminal:

```bash
python gemini_gateway.py # Hoặc tên tệp Python của bạn
```

Gateway sẽ khởi động và sẵn sàng nhận yêu cầu tại địa chỉ và cổng đã cấu hình (ví dụ: `http://0.0.0.0:8000`).

## Sử Dụng Gateway

Để gửi yêu cầu đến Gemini API thông qua gateway:

1.  **Endpoint:** Sử dụng URL của gateway (ví dụ: `http://localhost:8000`) theo sau là đường dẫn API của Gemini (ví dụ: `/v1beta/models/gemini-1.5-flash-latest:generateContent`).
2.  **Xác Thực Gateway:** Cung cấp `server_key` (đã định nghĩa trong `config.yaml`) thông qua:
    *   Header `X-Server-Key: YOUR_SECURE_GATEWAY_KEY`
    *   Query parameter `?key=YOUR_SECURE_GATEWAY_KEY`

Gateway sẽ tự động chọn một khóa API Gemini và proxy (nếu được kích hoạt và có sẵn) để xử lý yêu cầu.

**Ví dụ với `curl`:**

```bash
curl -X POST "http://localhost:8000/v1beta/models/gemini-1.5-flash-latest:generateContent" \
     -H "Content-Type: application/json" \
     -H "X-Server-Key: YOUR_SECURE_GATEWAY_KEY" \
     -d '{
           "contents": [{
             "parts":[{
               "text": "Translate 'hello' to Vietnamese."
             }]
           }]
         }'
```

## Các Endpoint của Gateway

*   **`/{full_path:path}` (GET, POST, PUT, DELETE):**
    *   Chuyển tiếp yêu cầu đến Gemini API. `full_path` tương ứng với đường dẫn API của Gemini.
    *   Yêu cầu xác thực bằng `server_key`.

*   **`/_gateway/health` (GET):**
    *   Cung cấp thông tin trạng thái của gateway, bao gồm số lượng proxy hoạt động, trạng thái kiểm tra sức khỏe, v.v.
    *   Không yêu cầu xác thực (theo mặc định).
    *   **Phản hồi mẫu:**
        ```json
        {
            "status": "healthy",
            "gemini_keys_available": 2,
            "health_checks_enabled": true,
            "whitelisted_proxies_count": 7,
            "recently_failed_proxies_tracked": 12,
            "min_whitelist_target": 5
        }
        ```

## Logging

Gateway ghi lại các thông tin vận hành quan trọng và lỗi vào console, hỗ trợ việc theo dõi và gỡ rối. Mức log mặc định là `INFO`.

## Lưu Ý Kỹ Thuật

*   **Cơ chế kiểm tra sức khỏe proxy:** Gateway gửi một yêu cầu GET đơn giản (ví dụ: liệt kê models) đến Gemini API thông qua từng proxy. Proxy được coi là khỏe mạnh nếu yêu cầu thành công (HTTP 200) trong khoảng thời gian chờ (`timeout_seconds`).
*   **Tích hợp `swiftshadow`:** Gateway sử dụng `swiftshadow` để lấy danh sách proxy ban đầu. Cấu hình và hoạt động của `swiftshadow` (ví dụ: nguồn proxy) nằm ngoài phạm vi trực tiếp của gateway này nhưng là một phần quan trọng của hệ thống.
