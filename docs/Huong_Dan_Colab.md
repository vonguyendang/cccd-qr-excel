# Hướng Dẫn Sử Dụng Trên Google Colab (Phiên Bản Tốc Độ Bàn Thờ)

Google Colab là một dịch vụ miễn phí của Google, cho phép bạn mượn máy tính của Google (với card đồ hoạ siêu mạnh - GPU T4) để chạy phần mềm quét CCCD/CMND này mà **không cần cài đặt bất kỳ thứ gì lên máy tính của bạn**.

Phiên bản Colab mới nhất đã được **tối ưu hóa luồng I/O và ép xung AI (ONNX-GPU)**. Tốc độ quét bằng AI trên GPU có thể nhanh gấp 10-20 lần so với chạy trên máy tính thường và tránh được tình trạng đứng máy khi đọc hàng ngàn file từ Google Drive.

---

## Chuẩn Bị (Rất Quan Trọng)
1. Một tài khoản Google (Gmail).
2. Trên máy tính của bạn, hãy gom tất cả các ảnh CCCD cần quét và **nén lại thành 1 file .zip duy nhất** (Ví dụ: `Anh_CCCD.zip`).
3. Tải file `Anh_CCCD.zip` đó lên **Google Drive** của bạn.

Việc nén thành file Zip và để Colab copy vào bộ nhớ nội bộ rồi mới giải nén sẽ giúp quá trình đọc file diễn ra chớp nhoáng, thay vì hệ thống phải kết nối mạng hàng ngàn lần để đọc từng tấm ảnh một.

---

## Các Bước Thực Hiện

### Bước 1: Mở File Google Colab
1. Trong thư mục gốc của dự án, bạn sẽ thấy file tên là `CCCD_QR_Excel_Colab.ipynb`.
2. Truy cập vào trang web [Google Colab](https://colab.research.google.com/).
3. Tại cửa sổ hiện lên, chọn thẻ **Upload** (Tải lên) và kéo thả file `CCCD_QR_Excel_Colab.ipynb` vào để mở.

### Bước 2: Bật GPU Siêu Tốc (Miễn phí)
1. Trên thanh menu trên cùng của trang web, chọn **Runtime** (Thời gian chạy) -> **Change runtime type** (Thay đổi loại thời gian chạy).
2. Ở phần *Hardware accelerator* (Trình tăng tốc phần cứng), hãy chọn **T4 GPU**.
3. Bấm **Save** (Lưu).

### Bước 3: Chạy Từng Khối Lệnh (Bấm Nút Play)

Trong file Colab, bạn chỉ cần bấm vào **Nút Play (hình tam giác)** ở bên trái của từng ô theo thứ tự từ trên xuống dưới.

1. **Chạy ô BƯỚC 1: Kết nối Google Drive**
   - Bấm nút Play. Google sẽ hiện bảng hỏi xin quyền truy cập vào Drive của bạn. Bấm "Cho phép".

2. **Chạy ô BƯỚC 2: Tải Mã Nguồn & Tối ưu hóa Thư viện GPU**
   - Bấm nút Play. Ô này sẽ tự động cài đặt công cụ ép xung GPU (`onnxruntime-gpu`) và các thư viện cần thiết. Chờ khoảng 1-2 phút đến khi hiện chữ `✅ Môi trường GPU T4 đã sẵn sàng...`.

3. **Chạy ô BƯỚC 3: Giải nén file ảnh siêu tốc**
   - Trước khi bấm Play, hãy điền đường dẫn tới file Zip ảnh trên Drive của bạn vào ô `file_zip_tren_drive`.
   - *Cách lấy đường dẫn:* Bấm vào biểu tượng Hình Thư Mục ở thanh công cụ bên trái màn hình Colab -> Mở thư mục `drive/MyDrive` ra -> Tìm đến file `Anh_CCCD.zip` của bạn -> Bấm chuột phải -> Chọn **Copy path** (Sao chép đường dẫn). Dán vào ô tương ứng.
   - Bấm nút Play. Colab sẽ chép file Zip siêu tốc và tự động giải nén trong tích tắc.

4. **Chạy ô BƯỚC 4: Kích hoạt Quét AI**
   - Bấm nút Play và ngồi xem AI cày cuốc hàng loạt ảnh của bạn với tốc độ xé gió!

5. **Chạy ô BƯỚC 5: Đóng gói và Copy kết quả về Google Drive**
   - Sau khi có thông báo QUÉT HOÀN TẤT ở Bước 4, chạy ô Bước 5.
   - Colab sẽ gói tất cả (File Excel, 5 thư mục ảnh phân loại) thành 1 file Zip gọn gàng và chép thẳng về một thư mục trên Google Drive của bạn có tên là `KetQua_CCCD`.
   - Lên Google Drive, tải file Zip mới nhất về máy và hưởng thụ thành quả!

---

## Câu Hỏi Thường Gặp (FAQ)

**1. Tại sao quá trình cài đặt (Bước 2) lại cần thiết lập `onnxruntime-gpu`?**
Mặc định hệ thống dùng `onnxruntime` thường (chỉ chạy CPU). Khi thiết lập `onnxruntime-gpu`, module Deepdoc VietOCR sẽ được đẩy hoàn toàn sang card T4 của Google, rút ngắn thời gian đọc văn bản tiếng Việt trên CCCD bị mất QR xuống còn 1/3.

**2. Tôi bị báo lỗi Out of Memory (Hết bộ nhớ)?**
Colab T4 có dung lượng RAM 16GB. Nếu file zip của bạn có kích thước quá khổng lồ (VD: 5GB ảnh) hoặc bạn nén hàng vạn tấm ảnh cùng lúc, Colab có thể quá tải ở khâu giải nén. Hãy chia file zip thành các gói nhỏ (khoảng 1000 - 2000 ảnh/gói) để đạt hiệu suất mượt mà nhất.

**3. Tại sao Google Drive của tôi không hiện?**
Đôi khi bạn cấp quyền xong nhưng nó load chậm. Hãy bấm lại vào ô Bước 1 hoặc tải lại trang trình duyệt web. Nếu trình duyệt chặn Cửa sổ bật lên (Popup), hãy nhớ cấp quyền cho phép nhé!
