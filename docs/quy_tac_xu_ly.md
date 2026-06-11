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

## Quy tắc Lưu trữ & Đồng bộ (Cập nhật Mới)

Hệ thống đã chuyển sang mô hình lưu trữ và đồng bộ hóa đa thiết bị dựa trên "Phiên làm việc" (Session/Room).

### 1. Quản lý Phiên (Session) & Trạng thái (State)
- Mọi thiết bị (Trình duyệt) truy cập Web App mặc định sẽ được cấp hoặc yêu cầu tham gia một **Mã Phiên (Room Code)**.
- Khi người dùng quét thành công, Web App không giữ kết quả cục bộ để làm Nguồn Dữ liệu Chính (Data Source) nữa, mà sẽ đẩy ngay lập tức kết quả (QR Data/OCR Data) lên API Backend `/api/room/add`.
- Backend (Python FastAPI) đóng vai trò là "Nguồn sự thật duy nhất" (Single Source of Truth). Dữ liệu thẻ CCCD sẽ được quản lý tập trung trong RAM của Backend.

### 2. Quy tắc Lọc Trùng lặp (Deduplication) Cấp độ Server
- Việc chống trùng lặp giờ đây được quản lý tập trung trên Server để đảm bảo tính nhất quán tuyệt đối khi nhiều thiết bị cùng quét.
- Server duy trì bộ đệm `seen_cccds` riêng biệt cho từng Mã phòng.
- **Quy tắc Ghi đè thông minh (OCR → QR):**
  - Nếu thẻ trước đó được quét bằng OCR (độ tin cậy thấp), và thẻ mới gửi lên được trích xuất bằng QR code (độ chính xác cao) có trùng số CCCD.
  - Server sẽ **CHẤP NHẬN** bản quét QR mới, và **GHI ĐÈ** xóa bản ghi OCR cũ.
  - Các trường hợp trùng lặp còn lại (QR trùng QR, OCR trùng OCR) đều bị Server chặn đứng và trả về lỗi `Duplicate CCCD`.

### 3. Quy tắc Đồng bộ Thời gian thực (WebSocket)
- Khi bất kỳ một thiết bị nào quét thêm thẻ thành công, Server sẽ Broadcast (phát sóng) tín hiệu cập nhật qua cổng WebSocket tới tất cả các thành viên đang kết nối chung Mã phòng.
- Màn hình của tất cả các thiết bị sẽ tự động đồng bộ (nhảy số lượng tổng, cập nhật thẻ mới vào danh sách) mà không cần tải lại trang.
- Tương tự, thao tác "Làm mới danh sách" (Clear) từ một người cũng sẽ lập tức xóa sạch màn hình của mọi người khác trong nhóm.

### 4. Quy tắc Backup Kép & Tự dọn rác 10 ngày (10-day Auto Cleanup)
- **Lớp Backup 1 (Trình duyệt):** Dữ liệu phiên vẫn được sao lưu định kỳ vào `localStorage` của trình duyệt sau mỗi lần nhận tín hiệu cập nhật từ WebSocket, nhằm chống lỗi rớt mạng cục bộ.
- **Lớp Backup 2 (Server JSON):** Server duy trì một thư mục lưu trữ vĩnh cửu `sessions/`. Mỗi khi có biến động dữ liệu, file JSON của phòng đó (VD: `sessions/XYZ123.json`) sẽ lập tức được cập nhật (Ghi đè). Tính năng này giúp người dùng cá nhân dễ dàng khôi phục dữ liệu ngày hôm trước chỉ bằng cách nhập lại Mã phiên.
- **Cơ chế Tự dọn dẹp (Auto Cleanup):** Để ngăn chặn rác hệ thống, mỗi file JSON đều được giám sát thời gian. Bất kỳ file nào nằm trong thư mục `sessions/` không có thay đổi (sửa đổi) sau đúng **10 ngày (864,000 giây)** sẽ tự động bị xóa vĩnh viễn khỏi Server.
