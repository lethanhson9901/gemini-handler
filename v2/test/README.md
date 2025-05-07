# 🌐 Gemini API Gateway (SwiftProxy + HealthCheck + Retry)

Đây là một **API Gateway tùy biến** cho Google Gemini, hỗ trợ:

* ✅ Quản lý và xoay vòng **nhiều API key**
* 🧠 Kiểm tra proxy đầu vào và duy trì **danh sách whitelist proxy khỏe**
* 🔁 Retry tự động khi gặp lỗi kết nối
* 🌐 Sử dụng proxy từ **SwiftShadow**
* 🧪 Fallback sang kết nối trực tiếp nếu không proxy nào khả dụng

---

## 🚀 1. Cài đặt môi trường

### Yêu cầu:

* Python 3.8+
* Hệ điều hành: Ubuntu/Linux/MacOS

### Cài thư viện:

```bash
pip install -r requirements.txt
```

> Tạo file `requirements.txt` với nội dung:

```txt
fastapi
uvicorn[standard]
httpx
pyyaml
swiftshadow
```

---

## ⚙️ 2. Cấu hình hệ thống

Tạo file `config.yaml` với nội dung mẫu sau:

```yaml
server_settings:
  server_key: "sk-1234"
  host: "0.0.0.0"
  port: 8000

gemini:
  base_url: "https://generativelanguage.googleapis.com"
  api_keys:
    - "AIzaSy..."  # Thêm các khóa Gemini API của bạn

proxy_settings:
  auto_update_interval_seconds: 60
  max_proxies: 100

retry_settings:
  max_request_retries: 2
  fallback_to_direct_on_failure: true
  retry_delay_seconds: 1

health_check_settings:
  enabled: true
  health_check_model_endpoint: "v1beta/models/gemini-2.0-flash"
  health_check_api_key: "AIzaSy..."
  timeout_seconds: 15
  max_concurrent_checks: 10
  min_whitelist_size: 5
  proxy_recheck_interval_seconds: 300
```

---

## ▶️ 3. Khởi chạy server

```bash
python gemini_gateway.py
```

> ✅ Server sẽ tự động khởi động tại `http://0.0.0.0:8000`

---

## 📡 4. Gửi request mẫu

### Gửi request `POST` đến Gemini API:

```bash
curl -X POST "http://localhost:8000/v1beta/models/gemini-2.0-pro:generateContent" \
     -H "Content-Type: application/json" \
     -H "X-Server-Key: sk-1234" \
     -d '{
       "contents": [{"role": "user", "parts": [{"text": "Viết một đoạn giới thiệu bản thân"}]}]
     }'
```

### Gửi request `GET` lấy danh sách model:

```bash
curl -X GET "http://localhost:8000/v1/models" \
     -H "X-Server-Key: sk-1234"
```

---

## 📊 5. Kiểm tra sức khỏe gateway

```bash
curl http://localhost:8000/_gateway/health
```

Kết quả mẫu:

```json
{
  "status": "healthy",
  "gemini_keys_available": 5,
  "health_checks_enabled": true,
  "whitelisted_proxies_count": 12,
  "recently_failed_proxies_tracked": 4,
  "min_whitelist_target": 5
}
```

---

## 🛡️ 6. Bảo mật API

* Mọi request phải đính kèm `X-Server-Key` header đúng như cấu hình `server_key`
* Hệ thống từ chối các truy cập không xác thực

---

## 💡 Ghi chú

* Proxy sẽ được kiểm tra định kỳ để đảm bảo hiệu suất
* Nếu tất cả proxy đều lỗi, hệ thống tự động fallback sang kết nối trực tiếp
* SwiftShadow tự động cập nhật danh sách proxy công cộng

---

Bạn có muốn mình tạo thêm ảnh mô tả kiến trúc hệ thống không?
