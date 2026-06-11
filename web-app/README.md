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

## Tùy chỉnh Cấu hình Hệ thống (config.js)

Để giúp việc tinh chỉnh trở nên dễ dàng và tập trung, hệ thống Web App đã được trang bị file cấu hình tổng. Bạn không cần phải tìm kiếm trong các file logic phức tạp nữa.

**Cách thực hiện:**
1. Mở file `web-app/assets/js/config.js`
2. Tại đây, bạn có thể dễ dàng thay đổi các thông số (lưu file và F5 trang web để áp dụng):

```javascript
const APP_CONFIG = {
    // Tùy chỉnh hiệu năng
    concurrencyLimit: 4,      // Số lượng ảnh được xử lý song song cùng lúc (Tăng lên nếu CPU/RAM mạnh)
    maxImageSize: 1500,       // Kích thước tối đa (pixel) khi nén ảnh trước khi gửi. Giảm xuống để chạy nhanh hơn nhưng có thể giảm độ chính xác.
    
    // Tùy chỉnh API
    apiScanQR: '/api/scan_qr',
    apiExportExcel: '/api/export',

    // Tùy chỉnh UI/UX
    successBeepVolume: 1.0,   // Âm lượng tiếng bíp thành công (0.0 đến 1.0)
    errorBeepVolume: 1.0      // Âm lượng tiếng bíp lỗi (0.0 đến 1.0)
};
```

**Lưu ý khi tăng tốc độ quét (`concurrencyLimit`):**
* **CPU (Chip xử lý):** Việc xử lý song song (đọc mã QR, nén ảnh, chạy nhận dạng OCR) tốn rất nhiều tài nguyên cục bộ. Chỉ nên thiết lập mức cao (trên 6 luồng) nếu máy tính dùng chip đa nhân mạnh (Apple M1+, Intel Core i7+). Tối ưu nhất là đặt số luồng **nhỏ hơn hoặc bằng** số nhân CPU thực tế.
* **Bộ nhớ RAM:** Mỗi luồng xử lý song song sẽ tiêu tốn thêm RAM để nạp dữ liệu ảnh gốc. Nếu thiết lập mức quá cao (ví dụ: `20`), tab trình duyệt có thể bị "Crash" (Out of Memory) do tràn bộ nhớ (đặc biệt khi tải ảnh nặng 5-10MB).
* **Nghẽn Web Worker:** Thư viện Tesseract OCR chạy trong các Worker ẩn của trình duyệt. Sinh ra quá nhiều Worker cùng lúc có thể gây nghẽn cổ chai khiến ứng dụng đơ giật. Nếu quạt rú mạnh hoặc liên tục báo lỗi, hãy chủ động giảm số luồng xuống!
