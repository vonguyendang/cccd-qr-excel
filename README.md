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
