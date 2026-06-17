# Quy tắc xử lý và trích xuất dữ liệu CCCD

Tài liệu này lưu trữ các quy định chung cho cả 2 ứng dụng Python và Web trong dự án.

## Cấu trúc dữ liệu QR

Mã QR trên thẻ Căn cước công dân chứa chuỗi ký tự phân tách bằng dấu `|`.
Ví dụ: `012345678912|123456789|Nguyễn Văn A|01011990|Nam|123 Đường Số 1, Phường 2, Quận 3, TP Hồ Chí Minh|01012022||||`

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
## Quy tắc Gộp Dữ Liệu 2 Mặt Thẻ (Merging)

Hệ thống sử dụng cơ chế gộp thông minh dựa trên "Số CCCD" làm khóa chính (Primary Key) để gom dữ liệu 2 mặt thẻ rời rạc thành một dòng duy nhất:
- **Ưu tiên QR:** Nếu thẻ mặt trước/sau quét bằng OCR (độ tin cậy thấp), và hệ thống phát hiện một mặt thẻ khác cùng số CCCD quét bằng QR (chính xác tuyệt đối), nó sẽ lấy dữ liệu QR để **GHI ĐÈ** lên dữ liệu OCR.
- **Bỏ qua trùng lặp:** Nếu cùng 1 CCCD mà quét nhiều lần (thừa ảnh), hệ thống sẽ giữ lại bản nét nhất/sớm nhất và đánh dấu các ảnh thừa là "Bỏ qua trùng lặp".
- **Bù trừ thông tin:** Dữ liệu mặt trước (Họ tên, Ngày sinh) sẽ tự động được đắp chung với dữ liệu mặt sau (Ngày cấp, Quê quán) để tạo thành một bộ hồ sơ đầy đủ 100%.

## Quy tắc Đóng gói File ZIP (Dành cho bản Terminal CLI)

Song song với việc xuất file Excel, phần mềm tự động phân loại và nén ảnh vào 5 file ZIP riêng biệt:
1. `original.zip`: Chứa toàn bộ file ảnh gốc ban đầu.
2. `rename.zip`: Chứa các file ảnh đã được nhận diện và đổi tên chuẩn theo định dạng `{Họ tên}_{CCCD/CMND}_Mặt trước/Mặt sau`. Được chia thư mục con theo loại thẻ (CCCD / CC).
3. `QR_scanned.zip`: Chứa các ảnh được đọc thành công bằng mã QR.
4. `OCR_scanned.zip`: Chứa các ảnh hỏng/mất mã QR, phải dùng đến AI OCR để bóc tách.
5. `duplicate.zip`: Chứa các ảnh rác, ảnh thừa, hoặc ảnh trùng lặp không sử dụng đến.
## Quy tắc gọi API chuẩn hóa Địa chỉ

Hệ thống kết nối đến API VNHub qua endpoint: `https://tienich.vnhub.com/api/wards`

- API được gọi theo phương thức `POST` bất đồng bộ (async) cho từng địa chỉ **độc nhất** (unique_addresses) xuất hiện trong lô thẻ để tăng tốc độ xử lý.
- Payload: `{"address": "chuỗi_địa_chỉ"}` với header xác thực `x-kas`.
- Trả về `success = true` và `data` hợp lệ → lấy kết quả ở `data[0].address` điền vào `Địa chỉ chuẩn hóa mới`.
- Trả về lỗi, rỗng hoặc `success = false` → bỏ trống cột chuẩn hóa, thêm lý do (VD: `Lỗi API...` hoặc `Không tìm thấy địa chỉ tương ứng`) vào cột `Ghi chú`.

## Quy tắc Trích xuất bằng AI (OCR)

Khi mã QR không thể đọc được, hệ thống (cả bản Web và Terminal) sẽ sử dụng AI OCR để đọc chữ từ ảnh.

- **Số CCCD:** Tìm chuỗi 12-15 ký tự bắt đầu bằng số 0 (Regex: `\b(0[\d\s]{11,15})\b`). Cho phép quét xuyên qua các khoảng trắng để khôi phục số CCCD bị đứt gãy do OCR nhận diện sai, sau đó tự động nối lại thành đúng 12 số nguyên bản.
- **Ngày sinh/Ngày cấp:** Tìm theo định dạng `dd/mm/yyyy` (cho phép khoảng trắng).
- **Giới tính:** Đếm số lần xuất hiện chữ `nam`. Hệ thống có cơ chế trừ hao các cụm từ chứa chữ "nam" nhưng là địa danh (như `việt nam`, `hà nam`, `quảng nam`, `hải nam`) để xác định chính xác giới tính.
- Dữ liệu OCR luôn có mức ưu tiên thấp hơn QR. Trong file Excel, các dòng OCR sẽ bị đẩy xuống dưới cùng và luôn có `Ghi chú: Lấy bằng OCR`.

## Quy tắc Giao diện & Log hệ thống (Terminal)

Phiên bản chạy dòng lệnh (Wizard CLI) được trang bị giao diện **Rich UI** tiên tiến:
1. **Định danh CCCD/CMND thông minh:** Hệ thống tự động nhận diện độ dài ID (12 số là CCCD, 9 số là CMND) để xưng hô chuẩn xác trong log.
2. **Đánh số thứ tự người dùng:** Trong quá trình gộp dữ liệu mặt trước/sau, mỗi người được đánh một số thứ tự duy nhất (Ví dụ: `[Người 1]`, `[Người 2]`), giúp dễ dàng theo dõi số lượng hồ sơ.
3. **Lưu vết Log File:** Toàn bộ tiến trình làm việc (bao gồm cả lỗi và màu sắc cảnh báo) được tự động xuất ra file `log_YYYYMMDD_HHMMSS.txt` song song với file Excel, tiện lợi cho việc tra soát sau này.

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
