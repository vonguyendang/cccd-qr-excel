# CCCD QR Excel - Web App

Ứng dụng web nội bộ dùng để quét mã QR từ hàng loạt ảnh CCCD, chuẩn hóa địa chỉ và xuất ra file Excel.

## Kiến trúc đặc biệt
Để xử lý hàng loạt 600+ ảnh mà không gây quá tải cho máy chủ (timeout, memory limit) cũng như không bắt buộc cấu hình lại `php.ini` quá phức tạp, ứng dụng này kết hợp:
- **Frontend (JS):** Sử dụng thư viện `jsQR` để đọc mã QR từ ảnh ngay trên trình duyệt của bạn. Trình duyệt sẽ đọc tất cả các file bạn chọn, tách mã QR thành văn bản.
- **Backend (PHP):** Nhận mảng văn bản từ Frontend (rất nhẹ), kết nối với API chuẩn hóa địa chỉ và sử dụng `PhpSpreadsheet` để xuất file Excel.

## Yêu cầu hệ thống
- PHP 7.4 trở lên.
- Các extension PHP bắt buộc cho PhpSpreadsheet: `php_zip`, `php_xml`, `php_gd2` (hoặc tương đương tuỳ hệ điều hành).
- Trình duyệt web hiện đại (Chrome, Edge, Firefox, Safari).

## Cài đặt thư viện
Bạn cần cài đặt Composer để tải `PhpSpreadsheet`.

Mở terminal trong thư mục `web-app` và chạy:
```bash
composer install
```

## Cấu hình API Chuẩn hóa (Tuỳ chọn)
Mặc định ứng dụng đang dùng API mock. Để dùng API thật, hãy cấu hình biến môi trường `ADDRESS_API_URL` cho Web Server (Apache/Nginx) hoặc export trước khi chạy PHP Server.

*Lưu ý: Nếu cần thay đổi cấu trúc payload gửi đến API, hãy sửa hàm `callAddressAPI` trong file `process.php`.*

## Hướng dẫn chạy thử (Local)
Bạn có thể dùng PHP Built-in Server để chạy nhanh trên máy tính:
```bash
# Đứng ở thư mục web-app
php -S 0.0.0.0:8000
```
Sau đó mở trình duyệt trên máy tính và truy cập: `http://localhost:8000`

### 📱 Hướng dẫn dùng Điện thoại quét Camera trực tiếp (Qua mạng nội bộ/Internet)
Tính năng **Live Camera Scanner** (Quét QR trực tiếp) trên điện thoại yêu cầu trình duyệt phải hoạt động ở chế độ bảo mật **HTTPS**. Nếu bạn chỉ gõ địa chỉ IP LAN (ví dụ: `http://192.168.1.5:8000`), Safari/Chrome trên điện thoại sẽ **chặn** quyền truy cập Camera.

Để giải quyết, bạn hãy sử dụng công cụ `localtunnel` (yêu cầu Node.js) để tạo một đường hầm HTTPS miễn phí:

1. Chạy PHP Server ở một Terminal:
```bash
php -S 0.0.0.0:8000
```
2. Mở một Terminal khác, chạy lệnh sau:
```bash
npx localtunnel --port 8000
```
3. Lệnh trên sẽ trả về một đường link có dạng `https://xxxx.loca.lt`.
4. Mở đường link này trên Điện thoại của bạn (có thể dùng 4G hoặc Wifi). Lần đầu truy cập hãy bấm "Click to Continue" nếu được hỏi.
5. Cấp quyền Camera và bắt đầu quét CCCD siêu tốc!

## Cách sử dụng
1. Ứng dụng có 2 chế độ (Tabs):
   - **📸 Live Camera:** Dùng camera để quét trực tiếp CCCD. Dữ liệu sẽ tự động được lưu đệm (Cache) trên trình duyệt, không sợ mất khi lỡ tải lại trang. Hỗ trợ phát âm thanh phản hồi (Bíp).
   - **📁 Tải Ảnh Lên:** Tải hàng loạt ảnh có sẵn để quét cục bộ.
2. Bạn có thể kết hợp cả 2 chế độ, kết quả sẽ gom chung vào danh sách Realtime bên dưới.
3. Nếu muốn xóa danh sách, bấm nút **Làm mới**.
4. Bấm **Xuất Excel ngay** để gửi toàn bộ dữ liệu hợp lệ lên server xử lý API chuẩn hóa và xuất ra file tải về. Dữ liệu đệm sẽ tự xóa sau khi xuất thành công.
