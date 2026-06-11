# Công Cụ Quét Mã QR CCCD Ra Excel Toàn Diện

Dự án này cung cấp một công cụ mạnh mẽ giúp bạn dễ dàng bóc tách thông tin từ mã QR trên Thẻ Căn cước công dân (CCCD) và xuất ra file Excel tự động. Hệ thống còn được tích hợp API (`tienich.vnhub.com`) để **chuẩn hóa địa chỉ thường trú gốc** sang tên đơn vị hành chính cấp xã/phường mới nhất.

Hệ thống được phát triển 100% bằng **Python** và cung cấp hai phương thức hoạt động để phù hợp với mọi nhu cầu:

1. **Chế độ Web App (Giao diện Web Trực quan):** Giao diện đẹp mắt, hỗ trợ upload hàng loạt ảnh, tự động phân tích và xuất file Excel. Hỗ trợ tính năng **Quét QR Trực tiếp từ Camera** (Live Scanner) của máy tính hoặc điện thoại! Web App có tích hợp sẵn mô hình Trí tuệ Nhân tạo (WeChat QRCode) siêu nhạy, đọc được cả ảnh lóa, mờ.
2. **Chế độ dòng lệnh CLI (Chạy ngầm):** Dành cho những ai muốn tự động hóa, chỉ cần gõ lệnh và cung cấp đường dẫn thư mục, công cụ sẽ âm thầm quét tất cả ảnh và tự động lưu ra file Excel.

## 🌟 Tính năng nổi bật
* Nhận diện mã QR chính xác tuyệt đối nhờ kết hợp các thư viện chuyên dụng (`pyzbar`, `ZXing`, `WeChatQRCode AI`).
* Nếu mã QR hỏng nặng, tự động dự phòng sang chế độ quét chữ (OCR bằng Tesseract).
* Tự động loại bỏ CCCD trùng lặp, chỉ lấy 1 dòng dữ liệu cho mỗi người.
* Kết nối API siêu tốc đa luồng (Multi-threading) để cập nhật và chuẩn hóa địa chỉ.
* Chạy Web App trên máy tính cá nhân, chia sẻ qua mạng để quét QR bằng camera điện thoại cực nhanh.

## 🛠 Hướng dẫn Cài đặt & Khởi động

Xem hướng dẫn chi tiết cho từng chế độ tại các thư mục thành phần:

* 👉 **[Hướng dẫn sử dụng Web App (Giao diện trực quan & Camera Mobile)](./web-app/README.md)**
* 👉 **[Hướng dẫn sử dụng Script CLI (Chạy bằng lệnh)](./python-app/README.md)**

## Yêu cầu Hệ thống
* Máy tính đã cài đặt sẵn Python 3.10+
* Nếu dùng OCR, yêu cầu cài đặt phần mềm [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) và gói ngôn ngữ tiếng Việt (`vie`).

## 🚀 Hướng dẫn Triển khai lên Hosting / VPS (Dành cho Production)

Do hệ thống sử dụng các thư viện AI, Xử lý ảnh (OpenCV) và quét mã (ZBar), phương pháp triển khai tốt nhất là sử dụng một máy chủ **Linux VPS (Ubuntu)** hoặc thông qua **Docker**. Các nền tảng Serverless (như Vercel/Netlify) không phù hợp vì không thể cài đặt các thư viện lõi hệ điều hành (`libzbar0`).

### Cách 1: Triển khai trực tiếp trên Ubuntu VPS
1. **Cài đặt thư viện hệ điều hành lõi:**
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv libzbar0 tesseract-ocr tesseract-ocr-vie
   ```
2. **Clone mã nguồn và cài đặt thư viện Python:**
   ```bash
   git clone <đường_dẫn_repo_của_bạn> cccd-qr-excel
   cd cccd-qr-excel
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # Lưu ý: Trên server Linux (không có giao diện màn hình), nên dùng opencv-python-headless
   pip uninstall opencv-python -y
   pip install opencv-python-headless
   ```
3. **Chạy Server bằng Uvicorn/Gunicorn:**
   - Để chạy nền liên tục, bạn có thể dùng `screen`, `tmux` hoặc cấu hình `systemd`.
   - Lệnh khởi chạy:
   ```bash
   cd python-app
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```
4. Mở port `8000` trên Firewall và truy cập thông qua `http://<IP_VPS>:8000`. 
   > **Lưu ý:** Để tính năng Camera quét QR hoạt động trên trình duyệt web, bắt buộc hệ thống phải chạy qua **HTTPS**. Bạn cần cấu hình thêm Nginx làm Reverse Proxy và lấy chứng chỉ SSL (Let's Encrypt).

### Cách 2: Triển khai thông qua Docker (Khuyên dùng)
Bạn có thể tự viết một file `Dockerfile` đơn giản với image base là `python:3.10-slim`.
1. Trong Dockerfile, nhớ thêm lệnh cài đặt thư viện lõi: `RUN apt-get update && apt-get install -y libzbar0 tesseract-ocr tesseract-ocr-vie`
2. Expose port `8000` và chạy CMD `uvicorn server:app --host 0.0.0.0 --port 8000`.
3. Triển khai Docker container lên các nền tảng như **Render**, **Railway**, hoặc **DigitalOcean App Platform**.

### Cách 3: Triển khai lên PythonAnywhere (Cần lưu ý)
PythonAnywhere mặc định sử dụng WSGI, trong khi FastAPI là một framework ASGI. Để chạy được trên PythonAnywhere, bạn cần sử dụng bộ chuyển đổi `a2wsgi`.
> **Cảnh báo quan trọng:** Môi trường PythonAnywhere bị khóa quyền `sudo`. Nếu tài khoản của bạn chưa được cài sẵn `libzbar0` và `tesseract-ocr` ở hệ điều hành, tính năng quét QR/OCR có thể sẽ bị lỗi. Lời khuyên là hãy gửi ticket cho support của PythonAnywhere nhờ họ cài đặt 2 thư viện này, hoặc mua gói trả phí hỗ trợ Custom Docker/Always-on tasks.

1. **Cài đặt thư viện:** Bật Bash Console trên PythonAnywhere và gõ:
   ```bash
   pip install fastapi uvicorn a2wsgi opencv-python-headless pyzbar openpyxl httpx
   ```
2. **Cấu hình Web app:**
   - Tạo một Web App mới trên PythonAnywhere, chọn **Manual configuration** (Python 3.10).
   - Mở file WSGI configuration (`/var/www/yourusername_pythonanywhere_com_wsgi.py`) và sửa thành:
   ```python
   import sys
   import os

   # Trỏ đường dẫn tới thư mục python-app
   path = '/home/yourusername/cccd-qr-excel/python-app'
   if path not in sys.path:
       sys.path.append(path)

   # Chuyển đổi ASGI (FastAPI) sang WSGI
   from server import app as fastapi_app
   from a2wsgi import ASGIMiddleware

   application = ASGIMiddleware(fastapi_app)
   ```
3. Lưu file WSGI và nhấn nút **Reload** ứng dụng. Lúc này FastAPI (Server) và giao diện Web App sẽ chạy thông qua tên miền HTTPS mặc định của PythonAnywhere.
