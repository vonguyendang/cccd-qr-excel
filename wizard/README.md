# Hướng dẫn Sử dụng Công cụ Dòng lệnh (CLI Script)

Công cụ dòng lệnh phù hợp khi bạn có một thư mục chứa rất nhiều file ảnh CCCD và muốn phần mềm chạy nền tự động xử lý một lần, không cần thao tác bấm từng file trên giao diện Web.

Chương trình sẽ tự động quét toàn bộ các file ảnh trong thư mục (bao gồm cả ảnh `.HEIC` từ iPhone), phân tích mã QR, chuẩn hóa địa chỉ thông qua API `tienich.vnhub.com`, lọc trùng lặp và lưu tất cả kết quả vào một file `.xlsx`.
Đồng thời, tự động đổi tên toàn bộ ảnh (theo định dạng `{Họ tên}_{CCCD/CMND}_Mặt trước/sau`) và nén thành 5 file phân loại:
1. `original.zip`: Ảnh gốc.
2. `rename.zip`: Ảnh đã đổi tên theo dữ liệu quét.
3. `QR_scanned.zip`: Các ảnh đọc được bằng mã QR.
4. `OCR_scanned.zip`: Các ảnh hỏng QR, phải đọc bằng AI OCR.
5. `duplicate.zip`: Các ảnh trùng lặp, ảnh lỗi hoặc không dùng đến.

**Tính năng vượt trội phiên bản mới:**
- Tích hợp **Rich UI** hiển thị sinh động, có thanh tiến trình và đánh số thứ tự hồ sơ `[Người 1]` trên Terminal.
- Tự động xuất kèm file `log_YYYYMMDD_HHMMSS.txt` lưu lại toàn bộ tiến trình báo cáo.
- Xử lý mượt mà lỗi "hiển thị thiếu 3 số" bằng thuật toán Regex quét ngang qua các điểm ngắt do xước thẻ.

Lưu ý: Giống như Web App, **bạn không cần phải cài đặt hay chạy riêng rẽ `deepdoc_vietocr`**. Nó đã được nhúng chung vào trong `main.py` và sẽ tự động khởi động.

## 🚀 Bước 1: Khởi động Môi trường ảo

Để chạy phần mềm tự động, chúng ta sẽ dùng chung "môi trường ảo" (nơi đã cài sẵn các thư viện AI nặng) của Web App để tránh việc phải tải lại model và cài đặt hai lần.

Bạn mở Terminal ở thư mục gốc (`cccd-qr-excel`) và gõ lần lượt các lệnh:

```bash
# 1. Di chuyển vào thư mục wizard
cd wizard

# 2. Kích hoạt môi trường ảo chung của phần webapp (nơi đã cài sẵn mọi AI)
# Trên Mac/Linux:
source ../webapp/venv/bin/activate
# Trên Windows:
# ..\webapp\venv\Scripts\activate

# 3. (Tuỳ chọn) Nếu bạn chưa cài đặt requirements ở Web App, bạn có thể cài tại đây:
pip install -r requirements.txt
```

## ⚙️ Bước 2: Chạy Phần Mềm Quét Tự Động

Sau khi môi trường `(venv)` đã được bật (bạn sẽ thấy chữ `(venv)` xuất hiện ở đầu dòng Terminal), chỉ cần gõ lệnh sau để khởi động phần mềm:

```bash
python3 main.py
```

1. Ở lần chạy đầu tiên, màn hình Terminal sẽ in ra thông báo *Đang khởi tạo AI Model Deepdoc_VietOCR (lần đầu sẽ mất vài giây)*. Bạn chờ một lát để AI được nạp vào RAM.
2. Chương trình sẽ yêu cầu bạn nhập **đường dẫn tới thư mục chứa file ảnh**. Bạn chỉ cần cầm thư mục chứa ảnh từ Finder/Explorer, kéo thả vào cửa sổ Terminal, nhấn phím `Enter`!
3. Cứ để kệ máy chạy. Mọi thao tác xử lý, đọc lỗi, gom ảnh mặt trước mặt sau, đổi tên file chương trình sẽ tự lo toàn bộ!
4. Quét xong, hệ thống sẽ tự động tạo một thư mục `exports/` nằm ngay bên trong thư mục `wizard/`. 
5. Toàn bộ thành quả (bao gồm file Excel, 5 file ZIP phân loại hình ảnh, và file Log chi tiết tiến trình) sẽ xuất hiện tại thư mục `wizard/exports/`. Mở lên và tận hưởng thôi!

---

## Cách xử lý các lỗi thường gặp khi cài đặt

**1. Lỗi `externally-managed-environment` khi gõ lệnh cài thư viện (`pip install`)**

- **Nguyên nhân:** Các hệ điều hành Mac/Linux mới chặn cài đặt thư viện tuỳ tiện để bảo vệ hệ thống.
- **Cách sửa:** Bạn cần tạo và dùng "môi trường ảo" thay vì cài trực tiếp. Hãy đảm bảo bạn đã chạy hai lệnh sau trước khi cài đặt:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

**2. Lỗi `ImportError: Unable to find zbar shared library` khi chạy chương trình**

- **Nguyên nhân:** Mặc dù đã cài thư viện python, nhưng máy tính (đặc biệt là máy Mac) bị thiếu bộ lõi quét mã vạch tên là `zbar` ở cấp hệ điều hành.
- **Cách sửa:** Bạn cần mở Terminal mới (bấm dấu `+`) và cài `zbar` qua Homebrew, sau đó tạo một liên kết để máy tính nhận diện. Copy và chạy toàn bộ dòng lệnh dài sau đây và ấn Enter:
  ```bash
  brew install zbar && mkdir -p ~/lib && ln -s $(brew --prefix zbar)/lib/libzbar.dylib ~/lib/libzbar.dylib
  ```

  Sau khi chạy xong, hãy quay lại thư mục phần mềm và chạy lệnh `python main.py` lại từ đầu.

**3. Phần mềm báo lỗi đỏ "Cannot find module cv2 / pyzbar" khi đang mở file code**

- **Nguyên nhân:** Do bạn đang mở source code bằng các phần mềm viết code (như VS Code), phần mềm này chưa nhận diện được "môi trường ảo" mà bạn đã tạo ở Bước 1.
- **Cách sửa:** Bạn hoàn toàn có thể **bỏ qua các vạch báo lỗi đỏ này**. Chỉ cần bạn thao tác đúng Bước 3 (chạy `source venv/bin/activate` trong Terminal) thì phần mềm vẫn sẽ chạy thành công 100%.
- **Nếu bạn mắc chứng "sợ màu đỏ" và muốn vạch đỏ biến mất trong VS Code, hãy làm như sau:**
  1. Nhấn tổ hợp phím `Cmd + Shift + P` (trên Mac) hoặc `Ctrl + Shift + P` (trên Windows).
  2. Gõ chữ `Python: Select Interpreter` và nhấn Enter.
  3. Chọn dòng `Enter interpreter path...` (Nhập đường dẫn...).
  4. Chọn tiếp `Find...` (Tìm kiếm...).
  5. Cửa sổ chọn file hiện ra, bạn hãy duyệt tìm đến thư mục chứa phần mềm này (`wizard`), mở tiếp thư mục `venv`, mở tiếp thư mục `bin` (hoặc `Scripts` trên Windows), và chọn file có tên là `python` (hoặc `python.exe`). Nhấn OK.
  6. Các vạch đỏ sẽ tự động biến mất!

**4. Lần chạy đầu tiên bị chậm / Có thông báo tải file**

- **Nguyên nhân:** Chương trình tích hợp trí tuệ nhân tạo (WeChat QRCode và Deepdoc VietOCR) nên ở lần chạy đầu tiên, mã nguồn sẽ tự động kết nối với máy chủ AI để tải mô hình chuẩn (nặng vài chục MB) vào bộ đệm cache.
- **Cách xử lý:** Đảm bảo có mạng và chờ vài phút. Lần chạy thứ 2 trở đi sẽ diễn ra siêu tốc!
