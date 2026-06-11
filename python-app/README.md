# Hướng Dẫn Sử Dụng Phầm Mềm Đọc CCCD (Dành Cho Người Không Rành Kỹ Thuật)

Chào bạn, đây là phần mềm giúp bạn quét hàng loạt ảnh chụp Căn cước công dân (CCCD), tự động lấy thông tin trong mã QR, chuẩn hóa lại địa chỉ theo hệ thống mới, và xuất ra một file Excel gọn gàng.

Bạn chỉ cần làm theo từng bước chậm rãi dưới đây nhé!

---

## Bước 1: Chuẩn bị ảnh
- Hãy gom tất cả hình ảnh CCCD (file đuôi `.jpg`, `.png`, v.v.) vào **chỉ 1 thư mục duy nhất**.
- Ví dụ: Tạo một thư mục ngoài màn hình Desktop tên là `Anh_CCCD` và bỏ hết ảnh vào đó.

## Bước 2: Khởi động phần mềm

Phần mềm này chạy trên "Terminal" (Cửa sổ dòng lệnh). Cách mở như sau:

**Nếu bạn dùng máy Mac (macOS):**
1. Nhấn tổ hợp phím `Command + Space` (hoặc nhấn vào icon Kính lúp ở góc trên phải màn hình).
2. Gõ chữ `Terminal` và nhấn `Enter`. Một cửa sổ nền đen/trắng sẽ hiện ra.

**Nếu bạn dùng máy Windows:**
1. Nhấn phím `Windows` (phím có hình lá cờ).
2. Gõ `cmd` hoặc `PowerShell` rồi nhấn `Enter`.

## Bước 3: Chạy chương trình

Trong cửa sổ Terminal vừa mở, bạn làm lần lượt 2 bước (copy dòng mã bên dưới rồi nhấn `Enter`):

**1. Di chuyển vào thư mục chứa phần mềm:**
```bash
cd /Volumes/MacintoshHD-Data/DATA/code/cccd-qr-excel/python-app
```
*(Nếu bạn đã chép phần mềm đi chỗ khác, hãy thay đoạn đường dẫn trên bằng đường dẫn tới thư mục `python-app` nhé).*

**2. Bật môi trường hoạt động và chạy phần mềm:**

- **Trên máy Mac/Linux:**
  ```bash
  source venv/bin/activate
  python3 main.py
  ```
- **Trên máy Windows:**
  ```cmd
  venv\Scripts\activate
  python main.py
  ```

## Bước 4: Nhập thư mục ảnh và nhận kết quả

1. Sau khi chạy lệnh `python3 main.py`, phần mềm sẽ chào bạn và yêu cầu nhập:
   > **Nhập đường dẫn thư mục chứa ảnh CCCD:**
2. Rất đơn giản, bạn chỉ cần **kéo thả cái thư mục** chứa ảnh CCCD (ví dụ thư mục `Anh_CCCD` ở Bước 1) **từ ngoài màn hình thả vào trong cửa sổ Terminal**. Nó sẽ tự điền đường dẫn cho bạn.
3. Nhấn `Enter`.
4. Đi uống một ngụm nước và chờ phần mềm tự động đọc ảnh, gửi địa chỉ đi chuẩn hóa, và lưu dữ liệu.
5. Khi hoàn tất, phần mềm sẽ báo tên file Excel (ví dụ: `ket_qua_20260611_103000.xlsx`). File Excel này nằm ngay bên trong thư mục `python-app` của phần mềm.

---

## Các lỗi thường gặp (Ghi chú Excel)
File Excel xuất ra có cột **Ghi chú** ở cuối cùng. Dưới đây là ý nghĩa của một số câu bạn có thể gặp:
- **Ảnh mờ/lóa / QR không đọc được**: Ảnh chất lượng kém, mã QR bị xước hoặc mờ, phần mềm không thể quét ra chữ.
- **Không tìm thấy địa chỉ tương ứng trong dữ liệu**: Địa chỉ cũ trên CCCD có thể không có trong hệ thống mới.
- **Địa chỉ chuyển đổi chưa chắc chắn**: Hệ thống có tìm thấy địa chỉ mới, nhưng độ tự tin không cao 100%, bạn nên ngó qua một chút để xác nhận.

---

## Cách xử lý các lỗi thường gặp khi cài đặt

**1. Lỗi `externally-managed-environment` khi gõ lệnh cài thư viện (`pip3 install`)**
- **Nguyên nhân:** Các hệ điều hành Mac/Linux mới chặn cài đặt thư viện tuỳ tiện để bảo vệ hệ thống.
- **Cách sửa:** Bạn cần tạo và dùng "môi trường ảo" thay vì cài trực tiếp. Hãy gõ lần lượt 3 lệnh sau (có dấu `venv`):
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip3 install -r requirements.txt
  ```

**2. Lỗi `ImportError: Unable to find zbar shared library` khi chạy chương trình**
- **Nguyên nhân:** Mặc dù đã cài thư viện python, nhưng máy tính (đặc biệt là máy Mac) bị thiếu bộ lõi quét mã vạch tên là `zbar` ở cấp hệ điều hành.
- **Cách sửa:** Bạn cần mở Terminal mới (bấm dấu `+`) và cài `zbar` qua Homebrew, sau đó tạo một liên kết để máy tính nhận diện. Copy và chạy toàn bộ dòng lệnh dài sau đây và ấn Enter:
  ```bash
  brew install zbar && mkdir -p ~/lib && ln -s $(brew --prefix zbar)/lib/libzbar.dylib ~/lib/libzbar.dylib
  ```
  Sau khi chạy xong, hãy quay lại thư mục phần mềm và chạy lệnh `python3 main.py` lại từ đầu.

**3. Phần mềm báo lỗi đỏ "Cannot find module cv2 / pyzbar" khi đang mở file code**
- **Nguyên nhân:** Do bạn đang mở source code bằng các phần mềm viết code (như VS Code), phần mềm này chưa nhận diện được "môi trường ảo" mà bạn đã tạo ở Bước 1.
- **Cách sửa:** Bạn hoàn toàn có thể **bỏ qua các vạch báo lỗi đỏ này**. Chỉ cần bạn thao tác đúng Bước 3 (chạy `source venv/bin/activate` trong Terminal) thì phần mềm vẫn sẽ chạy thành công 100%.
- **Nếu bạn mắc chứng "sợ màu đỏ" và muốn vạch đỏ biến mất trong VS Code, hãy làm như sau:**
  1. Nhấn tổ hợp phím `Cmd + Shift + P` (trên Mac) hoặc `Ctrl + Shift + P` (trên Windows).
  2. Gõ chữ `Python: Select Interpreter` và nhấn Enter.
  3. Chọn dòng `Enter interpreter path...` (Nhập đường dẫn...).
  4. Chọn tiếp `Find...` (Tìm kiếm...).
  5. Cửa sổ chọn file hiện ra, bạn hãy duyệt tìm đến thư mục chứa phần mềm này (`python-app`), mở tiếp thư mục `venv`, mở tiếp thư mục `bin` (hoặc `Scripts` trên Windows), và chọn file có tên là `python` (hoặc `python.exe`). Nhấn OK.
  6. Các vạch đỏ sẽ tự động biến mất!

Chúc bạn thao tác thành công! Nếu gặp khó khăn hãy nhờ bộ phận IT hỗ trợ bước cài đặt ban đầu nhé.
