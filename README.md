# CCCD QR Excel Project

Repository này chứa 2 ứng dụng độc lập dùng để giải quyết bài toán:
- Đọc mã QR từ ảnh CCCD (hỗ trợ hàng loạt 600+ ảnh).
- Tách thông tin từ chuỗi dữ liệu mã QR.
- Gọi API chuẩn hóa địa chỉ cũ sang địa chỉ mới theo lô (batch API).
- Xuất dữ liệu theo cấu trúc Excel quy định chuẩn.

## Cấu trúc thư mục

```text
cccd-qr-excel/
├─ python-app/      # Ứng dụng Python (CLI) chạy cục bộ
├─ web-app/         # Ứng dụng Web (PHP + JS) chạy cục bộ/intranet
├─ docs/            # Thư mục chứa tài liệu chung
├─ samples/         # Thư mục chứa các ảnh mẫu để test
└─ README.md        # File giới thiệu tổng quan dự án
```

Cả 2 ứng dụng hoạt động **hoàn toàn độc lập** với nhau. Bạn có thể chọn sử dụng 1 trong 2 tùy thuộc vào môi trường và sở thích của mình.

## Cấu trúc dữ liệu Excel

Cả 2 ứng dụng đều xuất ra file Excel với đúng 10 cột theo thứ tự bắt buộc:

| STT | Họ tên | CCCD | CMND | Giới tính | Ngày sinh | Nơi thường trú gốc | Địa chỉ chuẩn hóa mới | Ngày cấp CCCD | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|

- **Ngày sinh, Ngày cấp CCCD**: Định dạng `dd/mm/yyyy`.
- **Ghi chú**: Chứa lỗi ảnh không đọc được, dữ liệu trống, hoặc cảnh báo từ API (Ví dụ: "Không tìm thấy địa chỉ tương ứng trong dữ liệu", "Địa chỉ chuyển đổi chưa chắc chắn", "Ảnh mờ/lóa"). Các ghi chú được nối với nhau bằng dấu `; `.

## Hướng dẫn sử dụng chi tiết

Vui lòng xem `README.md` bên trong từng thư mục của ứng dụng để biết cách cài đặt và sử dụng:

- [Python App README](python-app/README.md)
- [Web App README](web-app/README.md)

## API Chuẩn hóa địa chỉ

Mặc định các ứng dụng đã thiết lập sẵn Mock (giả lập) việc gọi API để bạn có thể test ngay luồng hoạt động mà không cần API thật.
Để thiết lập API thật, hãy truyền URL vào biến môi trường `ADDRESS_API_URL` khi chạy. Logic gọi API được thiết kế theo lô (batch) tối đa 100 địa chỉ một lần để tối ưu hiệu suất.
