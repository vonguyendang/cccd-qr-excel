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
Bạn có thể dùng PHP Built-in Server để chạy nhanh:
```bash
# Đứng ở thư mục web-app
php -S localhost:8000
```
Sau đó mở trình duyệt và truy cập: `http://localhost:8000`

## Cách sử dụng
1. Click vào khu vực tải file và chọn toàn bộ ảnh CCCD cần xử lý (hỗ trợ chọn nhiều file một lúc).
2. Trình duyệt sẽ quét QR cục bộ (bạn có thể theo dõi tiến trình trên màn hình).
3. Sau khi quét xong, dữ liệu sẽ được gửi lên server.
4. Tải file Excel kết quả về máy.
