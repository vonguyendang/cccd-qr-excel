# Hướng dẫn Khởi chạy Web App & Live Scanner Camera

Hệ thống Web App cung cấp cho bạn một giao diện vô cùng thân thiện và tiện lợi, hỗ trợ hai chế độ làm việc:
1. **Upload File:** Chọn hàng loạt file ảnh lưu sẵn trên máy tính để đọc. Nếu có ảnh khó, Web App sẽ tự động đẩy xuống lõi Trí tuệ Nhân tạo (WeChat QRCode) của Python để bóc tách.
2. **Camera Scanner:** Truy cập trực tiếp Camera trên máy tính hoặc điện thoại di động để quét Live mã QR trên CCCD nhựa cứng một cách vô cùng nhanh nhạy và phát ra âm thanh báo hiệu.

Dữ liệu sau khi quét sẽ được gom vào bảng, tự động chuẩn hóa địa chỉ tại hệ thống VNHub, sau đó xuất ra tệp Excel khi bạn nhấn nút **Xuất Excel ngay**.

---

## Bước 1: Khởi động Máy chủ FastAPI (Backend & Web)

Toàn bộ hệ thống Web App và AI nay đã được hợp nhất thành một máy chủ **FastAPI (Python)** mạnh mẽ. Bạn cần mở Terminal ở thư mục gốc của dự án (`cccd-qr-excel`) và nhập lệnh:

```bash
cd python-app
source venv/bin/activate
# Lệnh dưới đây giúp tự động dọn dẹp cổng 8000 nếu đang bị kẹt (Dành cho máy Mac/Linux)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
# Khởi động máy chủ
uvicorn server:app --host 0.0.0.0 --port 8000
```
*(Nếu đây là lần đầu chạy, máy chủ sẽ tốn khoảng 3 giây để nạp Mô hình AI WeChat vào RAM bộ nhớ).*

> **Lưu ý cho người dùng Windows:**
> Nếu bạn dùng máy Windows và bị báo lỗi `[Errno 48] address already in use`, hãy mở PowerShell bằng quyền Admin, gõ lệnh `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force` trước khi chạy `uvicorn`.

Lúc này, bạn có thể truy cập thẳng Web App bằng trình duyệt trên máy tính tại địa chỉ:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## Bước 2: Chia sẻ Web App lên Điện thoại (Localtunnel)

Tính năng quét bằng Camera cần có mạng bảo mật `https` thì trình duyệt trên di động (iPhone/Android) mới cấp quyền bật máy ảnh. Chúng ta sẽ dùng tính năng tạo đường hầm Localtunnel.

**Hãy mở thêm một tab Terminal mới** tại thư mục gốc và gõ lệnh:

```bash
npx localtunnel --port 8000
```
*(Nếu máy chưa có NodeJS, hệ thống sẽ yêu cầu cài đặt npx tự động)*

Hệ thống sẽ trả về một đường link ngẫu nhiên (Ví dụ: `https://abcd-1234.loca.lt`).
1. Hãy dùng điện thoại di động truy cập vào đường link này.
2. Tại màn hình cảnh báo Tunnel, bấm chọn dòng **"Click to Continue"**.
3. Chuyển sang Tab "Sử dụng Camera" trên màn hình điện thoại, cấp quyền truy cập Camera và bắt đầu soi thẻ nhựa trực tiếp. 

> **Lưu ý:** Quét trên điện thoại xong, bộ đệm thông minh của Web App (Cache) sẽ lưu trữ dữ liệu lại. Bạn có thể nhấn tải về Excel ngay trên trình duyệt điện thoại để lưu trữ.

---

## Tùy chỉnh Tốc độ Quét (Số ảnh xử lý song song)

Mặc định hệ thống Web App sẽ xử lý **4 ảnh cùng lúc** (ở chế độ tải file) để cân bằng hiệu năng và tránh quá tải. Nếu máy tính bạn có cấu hình mạnh và muốn tăng tốc độ quét hàng loạt, bạn có thể tự tinh chỉnh giới hạn này.

**Cách thực hiện:**
1. Mở file `web-app/assets/js/app.js`.
2. Tìm dòng `const concurrencyLimit = 4;` (nằm ở khoảng dòng 440).
3. Thay đổi số `4` thành `8` hoặc `12` tùy ý, sau đó F5 tải lại trang web.

**Điều kiện & Lưu ý khi tăng luồng:**
* **CPU (Chip xử lý):** Việc xử lý song song (đọc mã QR, nén ảnh, chạy nhận dạng OCR) tốn rất nhiều tài nguyên CPU cục bộ của máy tính. Bạn chỉ nên thiết lập mức cao (trên 6 luồng) nếu máy tính dùng chip đa nhân mạnh (ví dụ: Apple M1/M2/M3, hoặc Intel Core i7/i9). Tối ưu nhất là đặt số `concurrencyLimit` **nhỏ hơn hoặc bằng** số nhân CPU thực tế của máy bạn.
* **Bộ nhớ RAM:** Mỗi luồng xử lý song song sẽ tiêu tốn thêm RAM để nạp dữ liệu ảnh gốc. Nếu bạn thiết lập mức quá cao (ví dụ: `20` hoặc `50`), tab trình duyệt có thể bị "Crash" (văng tab, Out of Memory) ngay lập tức do tràn bộ nhớ (đặc biệt khi tải lên toàn ảnh HEIC/PNG nặng 5-10MB).
* **Quá tải Web Worker:** Thư viện Tesseract OCR chạy trong các Worker ẩn của trình duyệt. Việc sinh ra quá nhiều Worker cùng lúc có thể gây nghẽn cổ chai khiến ứng dụng bị đơ giật. Nếu bạn thấy máy báo quạt rú mạnh hoặc một số file liên tục báo lỗi "Lỗi AI Backend", hãy chủ động giảm số luồng xuống!
