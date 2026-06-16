# Hướng dẫn Khởi chạy Web App & Quét Camera Trực tiếp

Hệ thống Web App cung cấp giao diện trực quan, hỗ trợ upload hàng loạt ảnh hoặc quét mã bằng Camera trên điện thoại. 
Lưu ý: Bạn **không cần phải khởi chạy riêng rẽ** mô hình `deepdoc_vietocr`. Toàn bộ AI OCR và WeChat QRCode đã được tích hợp sâu vào bên trong code Python, nó sẽ **tự động khởi chạy** cùng với máy chủ Web App!

## 🚀 Bước 1: Khởi động Máy chủ FastAPI (Backend)

Bạn cần mở Terminal ở thư mục gốc của dự án (`cccd-qr-excel`) và lần lượt làm theo các bước sau:

```bash
# 1. Di chuyển vào thư mục webapp
cd webapp

# 2. Tạo môi trường ảo riêng biệt (để cài đặt các thư viện AI không bị xung đột)
python3 -m venv venv

# 3. Kích hoạt môi trường ảo
# Trên Mac/Linux:
source venv/bin/activate
# Trên Windows:
# .\venv\Scripts\activate

# 4. Cài đặt toàn bộ thư viện cần thiết (Bao gồm cả Numpy, Torch cho Deepdoc_VietOCR)
pip install -r requirements.txt

# 5. Dọn dẹp cổng 8000 nếu đang bị kẹt (Chỉ dành cho máy Mac/Linux, có thể bỏ qua trên Windows)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# 6. Khởi động máy chủ Web App
uvicorn server:app --host 0.0.0.0 --port 8000
```

> **Ghi chú cực kỳ quan trọng ở lần chạy đầu tiên:**
> Máy chủ sẽ có thể tốn khoảng 1-2 phút "đứng hình" ở lần chạy đầu tiên để nạp các mô hình Trí tuệ Nhân tạo nặng vài chục MB (WeChat QRCode và các weights `cnn.onnx`, `transformerocr.pth` của Deepdoc VietOCR) vào bộ nhớ RAM. Hãy kiên nhẫn chờ cho đến khi thấy dòng chữ `Application startup complete`. Từ lần chạy thứ 2 trở đi, tốc độ sẽ là siêu tốc (dưới 1 giây)!

Lúc này, bạn có thể truy cập thẳng Web App bằng trình duyệt trên máy tính tại địa chỉ:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📱 Bước 2: Chia sẻ Web App lên Điện thoại (Localtunnel)

Tính năng quét bằng Camera cần có mạng bảo mật `https` thì trình duyệt trên di động (iPhone/Android) mới cấp quyền bật máy ảnh. Chúng ta sẽ dùng tính năng tạo đường hầm Localtunnel.

**Hãy mở thêm một tab Terminal mới** tại thư mục gốc và gõ lệnh:

```bash
npx localtunnel --port 8000
```
*(Nếu máy chưa có NodeJS, hệ thống sẽ yêu cầu tải npx tự động)*

Hệ thống sẽ trả về một đường link ngẫu nhiên (Ví dụ: `https://abcd-1234.loca.lt`).

1. Hãy dùng điện thoại di động truy cập vào đường link này.
2. Tại màn hình cảnh báo Tunnel, bấm chọn dòng **"Click to Continue"**.
3. Chuyển sang Tab "Sử dụng Camera", cấp quyền và bắt đầu soi thẻ nhựa trực tiếp. Dữ liệu sẽ đồng bộ liên tục về máy tính!

---

## ⚙️ Tùy chỉnh Cấu hình Hệ thống (config.js)

Để giúp việc tinh chỉnh trở nên dễ dàng, bạn có thể mở file `webapp/public/assets/js/config.js` để chỉnh sửa các thông số. Nhớ F5 trang web để áp dụng:

```javascript
const APP_CONFIG = {
    // Tùy chỉnh hiệu năng
    concurrencyLimit: 4,      // Số lượng ảnh được xử lý song song cùng lúc (Tăng lên nếu CPU/RAM mạnh)
    maxImageSize: 1500,       // Kích thước tối đa (pixel) nén ảnh trước khi gửi. Giảm xuống để chạy nhẹ hơn.
  
    // Tùy chỉnh API
    apiScanQR: '/api/scan_qr',
    apiExportExcel: '/api/export',

    // Tùy chỉnh UI/UX
    successBeepVolume: 1.0,   // Âm lượng tiếng bíp thành công
    errorBeepVolume: 1.0      // Âm lượng tiếng bíp lỗi
};
```

**Lưu ý khi tăng tốc độ quét (`concurrencyLimit`):**
Mỗi luồng xử lý song song sẽ tiêu tốn thêm RAM và CPU để chạy AI OCR Backend. Nếu đặt mức quá cao (ví dụ: `20`) trên máy yếu, API có thể bị nghẽn và sập Server. Tối ưu nhất là đặt số luồng bằng với số nhân CPU.
