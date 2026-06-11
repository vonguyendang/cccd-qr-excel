# Quy tắc xử lý và trích xuất dữ liệu CCCD

Tài liệu này lưu trữ các quy định chung cho cả 2 ứng dụng Python và Web trong dự án.

## Cấu trúc dữ liệu QR

Mã QR trên thẻ Căn cước công dân chứa chuỗi ký tự phân tách bằng dấu `|`.
Ví dụ: `093186002237|362499103|Nguyễn Thị Kim Thư|11011986|Nữ|56 Trần Hoàng Na, Kv6, An Khánh, Ninh Kiều, Cần Thơ|04102024||||`

Dữ liệu được map theo các index sau (từ 0):
- `0`: Số CCCD
- `1`: Số CMND (nếu có)
- `2`: Họ và tên
- `3`: Ngày sinh (ddmmyyyy)
- `4`: Giới tính
- `5`: Nơi thường trú gốc
- `6`: Ngày cấp CCCD (ddmmyyyy)

## Quy tắc xuất file Excel

File Excel bắt buộc phải có đủ 10 cột theo đúng thứ tự sau:

1. **STT**: Tự tăng từ 1
2. **Họ tên**: Giữ nguyên tiếng Việt có dấu
3. **CCCD**: Giữ nguyên chuỗi số
4. **CMND**: Có thì ghi, không có thì để trống
5. **Giới tính**: Giữ nguyên
6. **Ngày sinh**: Định dạng `dd/mm/yyyy` (chuyển từ `ddmmyyyy`)
7. **Nơi thường trú gốc**: Giữ nguyên gốc từ QR
8. **Địa chỉ chuẩn hóa mới**: Kết quả trả về từ API chuẩn hóa (`success = true`)
9. **Ngày cấp CCCD**: Định dạng `dd/mm/yyyy` (chuyển từ `ddmmyyyy`)
10. **Ghi chú**: Chứa lỗi ảnh không đọc được, dữ liệu trống, hoặc cảnh báo từ API. Các ghi chú nối với nhau bằng dấu `; `.

## Quy tắc gọi API chuẩn hóa

Hệ thống kết nối đến hệ thống chuẩn hóa qua endpoint: `https://diachi.io/api/convert-batch`

- Gọi API theo từng lô (batch), tối đa **100 địa chỉ / lần**.
- Trả về `success = true` và có `converted` → điền vào `Địa chỉ chuẩn hóa mới`.
- Trả về `notSure = true` → điền vào `Địa chỉ chuẩn hóa mới`, đồng thời thêm `Địa chỉ chuyển đổi chưa chắc chắn` vào cột `Ghi chú`.
- Trả về `success = false` → bỏ trống cột chuẩn hóa, thêm câu báo lỗi vào cột `Ghi chú` (VD: `Không tìm thấy địa chỉ tương ứng trong dữ liệu`).
