# Công Cụ Quét Mã QR CCCD Ra Excel Toàn Diện (Hỗ Trợ Thẻ Căn Cước Mới)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/vonguyendang/cccd-qr-excel/blob/main/CCCD_QR_Excel_Colab.ipynb)

Dự án này cung cấp một công cụ mạnh mẽ giúp bạn dễ dàng bóc tách thông tin từ mã QR và xử lý cả những trường hợp không có mã QR (quét bằng AI OCR) trên Thẻ Căn cước công dân (CCCD) và **Thẻ Căn cước mẫu mới (2024)**, sau đó xuất ra file Excel tự động.
Hệ thống còn được tích hợp API (`tienich.vnhub.com`) để **chuẩn hóa địa chỉ thường trú gốc** sang tên đơn vị hành chính cấp xã/phường mới nhất.

Hệ thống được phát triển 100% bằng **Python** và cung cấp hai phương thức hoạt động để phù hợp với mọi nhu cầu:

1. **Chế độ Web App (Giao diện Web Trực quan):** Giao diện đẹp mắt, hỗ trợ upload hàng loạt ảnh, tự động phân tích và xuất file Excel. Hỗ trợ tính năng **Quét QR Trực tiếp từ Camera** (Live Scanner) của máy tính hoặc điện thoại! Web App có tích hợp sẵn mô hình Trí tuệ Nhân tạo (WeChat QRCode) siêu nhạy, đọc được cả ảnh lóa, mờ.
2. **Chế độ dòng lệnh CLI (Chạy ngầm):** Dành cho những ai muốn tự động hóa, chỉ cần gõ lệnh và cung cấp đường dẫn thư mục, công cụ sẽ âm thầm quét tất cả ảnh và tự động lưu ra file Excel.

---

## 🌟 Tính năng nổi bật & Thuật toán Cốt lõi

### 1. Quét mã QR Siêu Tốc

- Nhận diện mã QR chính xác tuyệt đối nhờ kết hợp các thư viện chuyên dụng (`pyzbar`, `ZXing`, `WeChatQRCode AI`).
- Xử lý được các mã lóa sáng, mờ, xước.

### 2. Trải nghiệm Terminal Hiện Đại (Rich UI) & Logging Chuyên Sâu

- Giao diện dòng lệnh được thiết kế với **Rich**, cung cấp thanh tiến trình (Progress Bar), hiệu ứng Loading (Spinner), và màu sắc hiển thị sinh động.
- Tự động đánh số thứ tự cho từng người dùng `[Người 1]`, `[Người 2]` trong hệ thống log để dễ dàng giám sát quá trình gộp dữ liệu.
- Phân biệt xưng hô tự động giữa CCCD (12 số) và CMND (9 số).
- **Xuất File Log Chi Tiết:** Toàn bộ tiến trình chạy (kể cả cảnh báo lỗi) sẽ được kết xuất ra file văn bản `log_YYYYMMDD_HHMMSS.txt` song song với file Excel, giúp việc kiểm tra và đối chiếu trở nên cực kỳ thuận tiện.

### 3. Thuật toán AI OCR Đột Phá (Cho ảnh hỏng mã QR)

Khi mã QR không thể đọc được, hệ thống tự động kích hoạt mạng nén AI **Deepdoc VietOCR** (chuyên dụng tiếng Việt) để đọc chữ trực tiếp từ ảnh.
Thuật toán được chúng tôi "độ" lại với hàng loạt công nghệ bóc tách chuyên sâu:

- **Nhận diện mặt thẻ thông minh:** Phân loại chính xác 100% đâu là Mặt Trước, đâu là Mặt Sau dựa trên các cụm từ khóa chuyên biệt (VD: *Độc lập, Tự do* -> Mặt trước; *Đặc điểm nhận dạng* -> Mặt sau).
- **Phục hồi số thẻ từ mã MRZ:** Áp dụng chuẩn ICAO để đảo ngược và ghép nối mã MRZ ở đáy thẻ thành số thẻ 12 số hoàn chỉnh. Tự động sửa lỗi AI hay nhầm chữ `O` thành số `0`.
- **Cơ chế chống "cạm bẫy" Thẻ Căn cước mới:** Vượt qua hoàn hảo các lỗi hay gặp ở thẻ mẫu mới (2024) như:
  - Phân biệt rạch ròi *Ngày sinh*, *Ngày cấp*, và *Ngày hết hạn* (dù cả 3 đều có chữ "Ngày, tháng, năm").
  - Tránh bị nối nhầm *Nơi đăng ký khai sinh* vào *Nơi cư trú* ở mặt sau thẻ.
  - Ngăn ngừa tình trạng bắt nhầm Giới tính từ chữ "Nam" trong từ *Việt Nam* hay tên đường (*Trần Hoàng Nam*).
  - **Nhận diện xuyên khoảng trắng:** Thuật toán regex cực mạnh có khả năng quét qua các khoảng trống đứt đoạn của AI OCR để lấy lại nguyên vẹn 12 số CCCD, khắc phục triệt để lỗi "hiển thị thiếu 3 số".

### 4. Hợp nhất 2 Mặt Thẻ Bù Trừ (Pass 3 Merging)

Hệ thống sử dụng cơ chế thông minh: Nếu thẻ mất mã QR, nó sẽ dùng số CCCD (bóc từ MRZ) làm cầu nối để gộp dữ liệu ảnh mặt trước và ảnh mặt sau lại với nhau.
Ví dụ: Lấy *Họ tên, Ngày sinh* ở mặt trước đắp chung với *Ngày cấp, Quê quán* ở mặt sau. Đảm bảo file Excel cuối cùng luôn đầy đủ 100% cột dữ liệu!

### 5. Quản lý Ảnh và Đóng gói File ZIP

- Lọc bỏ triệt để các ảnh chụp thừa, chỉ giữ lại 1 dòng dữ liệu cho mỗi người.
- Cung cấp thêm 4 cột hình ảnh vào file Excel: "Ảnh mặt trước gốc", "Ảnh mặt sau gốc", và "Tên ảnh đã đổi".
- Đặc biệt với phiên bản Terminal (CLI), toàn bộ hình ảnh sau khi quét sẽ được tự động đổi tên (theo format `{Họ tên}_{CCCD/CMND}`) và phân loại nén vào **5 file ZIP riêng biệt**: `original.zip` (Ảnh gốc), `rename.zip` (Ảnh đã đổi tên), `QR_scanned.zip` (Ảnh quét bằng QR), `OCR_scanned.zip` (Ảnh phải dùng AI để đọc), và `duplicate.zip` (Ảnh rác/trùng lặp).

### 6. Multi-device Sync (Đồng bộ đa thiết bị)

- Kết nối Web App qua WebSocket, cho phép nhiều người/thiết bị cùng quét chung vào 1 phòng theo thời gian thực.
- Cơ chế "Backup Kép" (Dual Backup) tự động lưu trữ tiến trình ra file JSON. Có thể khôi phục lại dễ dàng và tự động dọn rác sau 10 ngày.

---

## 🛠 Hướng dẫn Cài đặt & Khởi động

Xem hướng dẫn chi tiết cho từng chế độ tại các thư mục thành phần:

* 🚀 **[Hướng dẫn chạy trực tiếp trên Google Colab (Tốc độ cao, Không cần cài đặt)](./docs/Huong_Dan_Colab.md)**
* 👉 **[Hướng dẫn sử dụng Web App (Giao diện trực quan &amp; Camera Mobile)](./webapp/README.md)**
* 👉 **[Hướng dẫn sử dụng Script CLI (Chạy bằng lệnh)](./wizard/README.md)**

## Yêu cầu Hệ thống

* Máy tính đã cài đặt sẵn Python 3.10+
* Nếu chạy lần đầu, quá trình nạp mô hình Trí tuệ nhân tạo (WeChat QRCode và Deepdoc OCR) sẽ tự động tải các file model nặng vài chục MB về máy. Vui lòng đảm bảo kết nối mạng.

> ⚠️ **Lưu ý CỰC KỲ QUAN TRỌNG về Phiên bản Thư viện (Dependency Hell):**
> Hệ thống kết hợp nhiều mô hình AI nên rất nhạy cảm với phiên bản thư viện. Bạn BẮT BUỘC phải dùng đúng các phiên bản đã được ghim trong `requirements.txt`:
>
> - `numpy<2.0.0`: PyTorch (lõi của VietOCR) sẽ bị lỗi "ARRAY_API not found" nếu dùng Numpy 2.x.
> - `opencv-contrib-python-headless==4.10.0.84`: Nếu cài bản mới hơn (như 4.13), module `cv2.wechat_qrcode` sẽ bị lỗi, gây hỏng tính năng quét QR siêu cấp.
> - `Pillow==10.2.0`: Các bản Pillow mới (>= 11.0) đã xóa bỏ một số hàm nội bộ khiến thư viện nhận diện chữ `vietocr` bị lỗi.

---

## 🚀 Hướng dẫn Triển khai lên Hosting / VPS (Dành cho Production)

Do hệ thống sử dụng các thư viện AI, Xử lý ảnh (OpenCV) và quét mã (ZBar), phương pháp triển khai tốt nhất là sử dụng một máy chủ **Linux VPS (Ubuntu)** hoặc thông qua **Docker**. Các nền tảng Serverless (như Vercel/Netlify) không phù hợp vì không thể cài đặt các thư viện lõi hệ điều hành (`libzbar0`).

### Cách 1: Triển khai trực tiếp trên Ubuntu VPS

1. **Cài đặt thư viện hệ điều hành lõi:**

   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv libzbar0 libgl1-mesa-glx
   ```
2. **Clone mã nguồn và cài đặt thư viện Python:**

   ```bash
   git clone <đường_dẫn_repo_của_bạn> cccd-qr-excel
   cd cccd-qr-excel
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r wizard/requirements.txt
   pip install -r webapp/requirements.txt
   pip install -r deepdoc_vietocr/requirements.txt
   # Lưu ý: Trên server Linux (không có giao diện màn hình), nên dùng opencv-python-headless
   pip uninstall opencv-python -y
   pip install opencv-python-headless
   ```
3. **Chạy Server bằng Uvicorn/Gunicorn:**

   - Lệnh khởi chạy:

   ```bash
   cd webapp
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```
4. Mở port `8000` trên Firewall và truy cập thông qua `http://<IP_VPS>:8000`.

   > **Lưu ý:** Để tính năng Camera quét QR hoạt động, bắt buộc hệ thống phải chạy qua **HTTPS**. Bạn cần cấu hình thêm Nginx làm Reverse Proxy.
   >

### Cách 2: Triển khai thông qua Docker (Khuyên dùng)

1. Trong Dockerfile, nhớ thêm lệnh cài đặt thư viện lõi: `RUN apt-get update && apt-get install -y libzbar0 libgl1-mesa-glx`
2. Expose port `8000` và chạy CMD `uvicorn server:app --host 0.0.0.0 --port 8000`.

### Cách 3: Triển khai lên PythonAnywhere (Cần lưu ý)

> **Cảnh báo quan trọng:** Môi trường PythonAnywhere bị khóa quyền `sudo`. Nếu tài khoản của bạn chưa được cài sẵn `libzbar0` và `tesseract-ocr`, tính năng quét QR/OCR có thể sẽ bị lỗi. Lời khuyên là hãy nhờ support cài đặt 2 thư viện này.

1. Bật Bash Console: `pip install fastapi uvicorn a2wsgi opencv-python-headless pyzbar openpyxl httpx`
2. Tạo Web App mới (Manual configuration - Python 3.10).
3. Mở file WSGI configuration và sửa thành:
   ```python
   import sys
   path = '/home/yourusername/cccd-qr-excel/webapp'
   if path not in sys.path:
       sys.path.append(path)

   from server import app as fastapi_app
   from a2wsgi import ASGIMiddleware
   application = ASGIMiddleware(fastapi_app)
   ```
4. Lưu và nhấn **Reload**.
