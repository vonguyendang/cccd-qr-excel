# Hướng dẫn Chạy Tự Động Hàng Loạt (Wizard CLI)

Công cụ dòng lệnh phù hợp khi bạn có một thư mục chứa rất nhiều file ảnh CCCD và muốn phần mềm chạy nền tự động xử lý một lần (ví dụ: cắm máy chạy qua đêm), không cần thao tác bấm từng file trên giao diện Web.

Chương trình sẽ tự động quét toàn bộ các file ảnh trong thư mục, phân tích mã QR, hoặc tự động kích hoạt `deepdoc_vietocr` để quét chữ nếu QR hỏng. Sau đó tự xuất toàn bộ ra một file `.xlsx` và tự động đổi tên/nén ảnh.

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
4. Quét xong, file Excel sẽ xuất hiện ngay trong thư mục gốc với tên dạng `ket_qua_ngay_gio.xlsx`.

---

## 🛠 Xử lý các lỗi có thể gặp

**1. Lỗi `externally-managed-environment` khi gõ lệnh cài thư viện (`pip install`)**
- Đây là lỗi bảo mật của Mac/Linux. Khắc phục bằng cách bắt buộc dùng môi trường ảo `venv` như hướng dẫn ở Bước 1.

**2. Lỗi `ImportError: Unable to find zbar shared library`**
- **Sửa lỗi trên Mac:** Mở Terminal mới, cài `zbar` bằng dòng lệnh sau:
  ```bash
  brew install zbar && mkdir -p ~/lib && ln -s $(brew --prefix zbar)/lib/libzbar.dylib ~/lib/libzbar.dylib
  ```

**3. VS Code báo vạch đỏ "Cannot find module cv2 / pyzbar / vietocr"**
- **Cách sửa:** Do VS Code chưa được chọn đúng Interpreter. Bạn nhấn `Cmd + Shift + P` -> Gõ `Python: Select Interpreter` -> Trỏ đường dẫn vào thư mục `../webapp/venv/bin/python`. Hoặc đơn giản là **KỆ NÓ**, vạch báo đỏ trên màn hình code không làm ảnh hưởng đến khả năng chạy lệnh trên Terminal!
