# Hướng Dẫn Chi Tiết Từng Bước Các Luồng Xử Lý (CCCD-QR-Excel)

Tài liệu này mô tả chi tiết từng bước hoạt động của mỗi luồng chính, các luồng con bên trong hệ thống, cùng với các bước hướng dẫn cụ thể và lưu ý/cảnh báo cho người dùng trong từng trường hợp.

---

## A. Khái Niệm & Nguyên Lý Hoạt Động Của 3 Luồng Xử Lý Chính

Trong mọi môi trường (Web App, CLI, Colab), quá trình quét được thiết kế thông minh để tự động thích ứng với 3 trạng thái/luồng dữ liệu như sau:

### 1. Luồng Quét Mới (Fresh Scan)
**Mục đích:** Khởi tạo một phiên làm việc mới tinh từ đầu đến cuối cho một thư mục ảnh.

**Chi tiết luồng hoạt động:**
- **Bước 1 (Đọc file):** Quét toàn bộ thư mục, tìm mọi định dạng ảnh (JPG, PNG, HEIC...).
- **Bước 2 (Giải mã QR đa tầng):** Đẩy từng ảnh qua 3 lớp thư viện quét mã vạch (PyZBar -> ZXing -> WeChatQRCode AI) để tìm mã QR siêu tốc.
- **Bước 3 (Bóc tách AI OCR):** Nếu QR hỏng, tự động cắt vùng chứa chữ, tăng tương phản ảnh và đẩy qua mạng neural AI (Deepdoc VietOCR) để đọc chữ tiếng Việt.
- **Bước 4 (Chuẩn hóa API):** Gửi dữ liệu Nơi thường trú lên máy chủ `tienich.vnhub.com` để map lại thành cấu trúc Tỉnh/Huyện/Xã chuẩn mới nhất.
- **Bước 5 (Hợp nhất Pass 3 Merging):** Dùng Số CCCD làm ID duy nhất. Gom ảnh mặt trước và mặt sau của cùng 1 người lại, đắp bù các trường thông tin chéo cho nhau (VD: Lấy Ngày Sinh mặt trước đắp chung với Dấu Vân Tay mặt sau).
- **Bước 6 (Lọc rác):** Giữ lại ảnh rõ nét nhất nếu 1 người chụp thừa nhiều ảnh, loại bỏ ảnh thừa vào `duplicate.zip`.
- **Bước 7 (Xuất báo cáo):** Đóng gói 5 file ZIP phân loại ảnh và xuất 1 file Excel tổng hợp hoàn chỉnh.

### 2. Luồng Quét Nối Tiếp (Resume / Sequential Scan)
**Mục đích:** Cứu vãn các phiên làm việc bị gián đoạn (mất điện, tắt nhầm máy, hoặc chia nhỏ quét nhiều đợt) mà không phải chạy lại từ đầu.

**Chi tiết luồng hoạt động:**
- **Bước 1 (Nhận diện Cache):** Khi bạn nạp lại *cùng thư mục ảnh* đó, hệ thống lập tức tìm kiếm file `.json` hoặc file Excel dở dang ở trong thư mục `exports/` (hoặc Local Storage trên Web App).
- **Bước 2 (Kiểm đếm tệp tin đã xử lý):** Hệ thống lập chỉ mục (index) toàn bộ các tên file ảnh đã có sẵn kết quả xanh chín trong bộ đệm.
- **Bước 3 (Bỏ qua tốc độ cao):** Khi bắt đầu quét, nó lập tức `SKIP` (bỏ qua) các ảnh đã nằm trong bộ nhớ cache. Thanh tiến trình sẽ nhảy vọt (Ví dụ: *"Phát hiện dữ liệu cũ, bỏ qua 1500 ảnh đã quét..."*).
- **Bước 4 (Tiếp tục công việc):** Hệ thống chỉ thực sự khởi động luồng AI để bóc tách những ảnh mới chưa từng được xử lý.
- **Lưu ý quan trọng:** Để luồng này hoạt động, BẮT BUỘC bạn không được xóa hay di chuyển các file kết quả dở dang trong thư mục `exports`.

### 3. Luồng Tái Xử Lý (Reprocessing / Retry)
**Mục đích:** Sửa sai và đắp bù thông tin. Thay vì quét lại cả ngàn ảnh từ đầu, luồng này giúp bạn chỉ quét lại đúng vài chục người bị mờ/hỏng trong file Excel cũ.

**Chi tiết luồng hoạt động:**
- **Bước 1 (Đọc file Excel cũ):** Thay vì nạp thư mục ảnh, bạn nạp file `.xlsx` cũ vào hệ thống. Hệ thống tự quét qua toàn bộ các dòng.
- **Bước 2 (Lọc hồ sơ lỗi):** Nó đánh dấu các hồ sơ cần quét lại nếu: (1) Thiếu thông tin ở cột quan trọng (Họ tên, Ngày sinh, Quê quán...), hoặc (2) Cột "Ghi chú" báo lỗi phải `Lấy bằng OCR` ở lần quét trước.
- **Bước 3 (Truy quét ảnh mới):** Đối chiếu file Excel với thư mục ảnh thực tế. Nếu bạn vừa thả thêm vài ảnh mới tinh vào thư mục, nó cũng tự gom chung vào để xử lý.
- **Bước 4 (Ép AI chạy tối đa công suất):** Trích xuất lại ảnh mặt trước/sau của các hồ sơ lỗi. Đẩy thẳng vào bộ lọc ảnh chuyên sâu (Tăng tương phản CLAHE, Cắt Otsu nâng cao, xoay chiều ảnh) và ép AI OCR đọc đi đọc lại đa luồng để vắt kiệt dữ liệu.
- **Bước 5 (Đắp bù trực tiếp - In-place Merge):** Phần mềm KHÔNG tạo ra file Excel mới. Nó đắp bù trực tiếp các thông tin vừa cứu được vào đúng các ô bị trống trong file Excel cũ. Các dòng đã xanh chín từ trước được giữ nguyên tuyệt đối.
- **Bước 6 (Báo cáo tỷ lệ cứu sống):** In ra bảng thống kê số ảnh được cứu thành công bằng QR/OCR và tốc độ xử lý.

---

## 1. Luồng 1: Sử Dụng Web App (Giao Diện Trực Quan)

**Mục đích:** Phù hợp cho người dùng phổ thông, muốn tải ảnh lên trực tiếp từ máy tính hoặc dùng điện thoại làm máy quét Camera (Live Scanner). Hỗ trợ đồng bộ nhiều thiết bị.

### Hướng Dẫn Từng Bước:
1. **Bước 1: Khởi động Server Web**
   - Mở Terminal, di chuyển vào thư mục dự án gốc.
   - Kích hoạt môi trường ảo: 
     - Mac/Linux: `source .venv/bin/activate`
     - Windows: `.\.venv\Scripts\activate`
   - Di chuyển vào thư mục: `cd webapp`.
   - Khởi động máy chủ: `uvicorn server:app --host 0.0.0.0 --port 8000`.
2. **Bước 2: Truy cập Web App**
   - Mở trình duyệt web và truy cập vào `http://localhost:8000`.
   - Để dùng điện thoại quét Live, đảm bảo điện thoại và máy tính chung mạng Wifi, truy cập `http://<IP_Máy_Tính_Của_Bạn>:8000`.
3. **Bước 3: Tải Ảnh Hoặc Quét Live**
   - *Luồng Quét Mới:* Kéo thả hàng loạt ảnh mới vào khu vực Upload, hoặc nhấn Quét Camera.
   - *Luồng Quét Nối Tiếp:* Nếu vô tình F5 trang web, khi vào lại, Web App sẽ tự load lại dữ liệu cũ từ Local Storage/WebSocket. Bạn chỉ việc tiếp tục quét các ảnh còn lại.
   - *Luồng Tái Xử Lý:* Những ảnh bị báo đỏ (Không đọc được), bạn có thể click vào nút "Quét lại ảnh này bằng OCR tăng cường".
4. **Bước 4: Xử Lý và Xuất Excel**
   - Hệ thống tự động ghép mặt trước và mặt sau dựa vào Số CCCD.
   - Bấm nút `Xuất Excel` để tải danh sách về máy.

> **⚠️ Nhắc nhở người dùng (Các trường hợp cần lưu ý):**
> - **Lỗi Camera không hoạt động:** Trình duyệt sẽ chặn quyền Camera nếu không sử dụng HTTPS (trừ `localhost`). Hãy dùng `ngrok` để tạo link HTTPS nếu cần quét bằng điện thoại.
> - **Treo máy do tải AI:** Ở lần chạy đầu tiên, màn hình có thể đứng hình vài giây do tải mô hình.

---

## 2. Luồng 2: Sử Dụng CLI / Wizard (Xử Lý Tự Động Hàng Loạt)

**Mục đích:** Xử lý tự động hoàn toàn hàng trăm, hàng ngàn ảnh CCCD trong một thư mục rỗng tuếch, tự đổi tên, phân loại file ZIP và xuất Excel.

### Hướng Dẫn Từng Bước:
1. **Bước 1: Khởi động Môi trường và Script**
   - Mở Terminal tại `cccd-qr-excel`.
   - Kích hoạt môi trường ảo: `source .venv/bin/activate`.
   - Vào thư mục wizard: `cd wizard`.
   - Chạy: `python3 main.py`.
2. **Bước 2: Cung cấp Đường Dẫn Thư Mục Ảnh**
   - Kéo thả thư mục chứa ảnh CCCD vào cửa sổ Terminal và nhấn Enter.
3. **Bước 3: Hệ Thống Tự Động (Auto-Flow & Sub-flows)**
   - *Luồng Quét Mới:* Thanh tiến trình (Progress Bar) chạy từ đầu. Tự động sao lưu tiến trình (Realtime Backup), có thể bấm Ctrl+C để dừng và chạy tiếp bất cứ lúc nào.
   - *Luồng Quét Nối Tiếp:* Nếu trước đó bạn đã quét thư mục này nhưng bị dừng, hệ thống sẽ thông báo và tự động khôi phục dữ liệu từ file backup JSON để chạy tiếp các ảnh còn lại.
   - *Luồng Tái Xử Lý (Chuyên sâu):* Khi bạn nhập file Excel kết quả cũ vào, hệ thống cung cấp 3 chế độ tái xử lý mạnh mẽ:
     - **Mode 1 (Tái bổ sung thông tin OCR):** Chuyên dùng để quét lại các dòng ảnh báo lỗi hoặc thiếu trường thông tin (VD: Tôn giáo, Quê quán) bằng AI OCR tăng cường. Nó đắp bù trực tiếp dữ liệu mới vào file Excel gốc mà không ghi đè dữ liệu cũ.
     - **Mode 2 (Làm đẹp & Chuẩn hóa toàn bộ):** KHÔNG gọi AI tốn thời gian. Chế độ này dùng để tẩy rác, xóa ký tự thừa cho tên/địa chỉ theo luật `ocr_rules.json`, sau đó gọi API chuẩn hóa.
     - **Mode 3 (Chỉ chuẩn hóa):** Cập nhật lại cấu trúc địa chỉ mới từ VNHub/Geovina mà không thay đổi địa chỉ gốc ban đầu.
4. **Bước 4: Nhận Thành Quả**
   - Mở thư mục `wizard/exports/`.
   - Nhận 1 file `.xlsx`, 1 file Log tiến trình và 5 file ZIP phân loại (Original, Rename, QR_scanned, OCR_scanned, Duplicate).

> **⚠️ Nhắc nhở người dùng (Các trường hợp cần lưu ý):**
> - **Lỗi `libzbar.dylib` hoặc `cv2`:** Do thiếu thư viện lõi hệ điều hành. Mac: `brew install zbar`, Ubuntu: `sudo apt install libzbar0`.
> - **Ảnh iPhone (.HEIC):** Công cụ đã tích hợp sẵn module HEIC, không cần đổi đuôi thủ công.
> - **Thời gian ở bước Tái xử lý OCR:** Với ảnh mờ lóa, bước tái xử lý OCR (chạy Deepdoc) tốn 3-5 giây/ảnh. Thanh tiến trình sẽ chạy chậm lại, đây là trạng thái bình thường.

---

## 3. Luồng 3: Chạy Trên Google Colab (Môi Trường Đám Mây)

**Mục đích:** Chạy phần mềm mà không cần cài đặt, dùng tài nguyên GPU mạnh của Google.

### Hướng Dẫn Từng Bước:
1. **Bước 1: Mở File Notebook**
   - Mở `CCCD_QR_Excel_Colab.ipynb` hoặc bấm vào "Open In Colab" trên Github.
2. **Bước 2: Chuẩn Bị File ZIP**
   - Nén tất cả ảnh của bạn vào file `data.zip` và upload lên mục Files bên trái Colab.
   - *Luồng Quét Mới:* Cứ đẩy file ZIP lên và chạy từ khối lệnh đầu.
   - *Luồng Tái Xử Lý / Quét Nối Tiếp:* Nếu bị đứt gánh giữa chừng trên Colab, bạn nên lọc sẵn các ảnh chưa quét trên máy tính cá nhân thành một file `data2.zip` và upload lên để chạy riêng, nhằm tránh bị quá giới hạn thời gian chạy của Google.
3. **Bước 3: Chạy Tuần Tự Các Khối Lệnh**
   - Dùng phím `Shift + Enter` chạy qua từng block. Kệ thông báo "Restart Runtime" đỏ ở block cài đặt.
4. **Bước 4: Xử Lý Mật Khẩu (Nếu Có)**
   - Nếu ZIP có mật khẩu, Colab sẽ hiển thị TextBox để bạn nhập.
5. **Bước 5: Tải Kết Quả**
   - Click vào các đường link được tạo ra ở Output block cuối cùng để tải Excel và 5 file ZIP về.

> **⚠️ Nhắc nhở người dùng (Các trường hợp cần lưu ý):**
> - **Giới hạn RAM / Crash:** Nếu file ZIP > 2GB, Colab miễn phí sẽ sập. Phải chia nhỏ (Quét mới theo từng đợt).
> - **Ephemeral Storage (Dữ liệu tạm):** File trên Colab bị xóa khi đóng tab hoặc disconnect. Bắt buộc tải Excel về ngay khi có kết quả.

---

## 4. Mô Tả Chi Tiết Auto-Flow Bên Trong Hệ Thống

Để đảm bảo hiệu suất cho mọi "Luồng con" (Mới, Nối tiếp, Tái xử lý), Back-end sẽ luân chuyển dữ liệu như sau:

1. **Luồng Quét QR Liên Hoàn (Tốc độ):**
   - Chạy 3 thư viện: `PyZBar` -> (lỗi) -> `ZXing` -> (lỗi) -> `WeChatQRCode AI`.
2. **Luồng Tái Xử Lý AI OCR (Sâu):**
   - Chỉ được gọi khi quét QR thất bại hoàn toàn. 
   - Kích hoạt thuật toán bù sáng, chạy Deepdoc OCR tiếng Việt, và vá chuỗi bằng Regex để khắc phục lỗi mất số.
3. **Luồng Chuẩn Hóa Địa Chỉ (VNHub):**
   - Đẩy dữ liệu lên `tienich.vnhub.com` để map lại theo Tỉnh/Huyện/Xã chuẩn hiện tại.
4. **Luồng Hợp Nhất (Pass 3 Merging):**
   - Dùng chung ID (Số CCCD/CMND) ghép mặt trước, mặt sau với nhau. Bù đắp dữ liệu chéo nhau.
5. **Luồng Lọc Trùng Lặp:**
   - Trong 1 luồng quét, hệ thống tự bắt các bức ảnh chụp nhiều lần cho 1 mặt thẻ, giữ ảnh tốt nhất, đẩy ảnh thừa vào `duplicate.zip`.
6. **Cơ chế Sao Lưu & Cứu Hộ Thời Gian Thực (Realtime Recovery):**
   - Mọi tiến trình quét ảnh OCR hay gọi API đều được lưu nháp lập tức ra file JSON Lines (`_reprocess_recovery.jsonl`, `_api_recovery.jsonl`). Chống mất trắng dữ liệu khi cúp điện, mất mạng hay dừng đột ngột bằng Ctrl+C. Hệ thống cũng tích hợp cơ chế tự động theo dõi tốc độ dòng/giây (it/s) để người dùng dễ kiểm soát tiến độ.
