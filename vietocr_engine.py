import os
import sys
import numpy as np
from PIL import Image

# Thêm thư mục deepdoc_vietocr vào PYTHONPATH
base_dir = os.path.dirname(os.path.abspath(__file__))
deepdoc_path = os.path.join(base_dir, 'deepdoc_vietocr')
if deepdoc_path not in sys.path:
    sys.path.insert(0, deepdoc_path)

from module.ocr import OCR

# Thread-local storage: mỗi thread giữ instance model riêng, tránh lỗi PyTorch khi đa luồng
import threading
_thread_local = threading.local()

def get_ocr_engine():
    if not hasattr(_thread_local, 'ocr_instance') or _thread_local.ocr_instance is None:
        print("Đang khởi tạo AI Model Deepdoc_VietOCR (lần đầu sẽ mất vài giây)...")
        _thread_local.ocr_instance = OCR()
    return _thread_local.ocr_instance

def extract_text_from_image(img, return_orientation=False):
    """
    Trích xuất text tiếng Việt từ ảnh (numpy array hoặc PIL Image)
    """
    if isinstance(img, Image.Image):
        img_array = np.array(img.convert('RGB'))
    else:
        img_array = img
        
    try:
        ocr = get_ocr_engine()
        bxs = ocr(img_array, 0) # device_id = 0
        if not bxs:
            return ("", False) if return_orientation else ""
            
        lines = [item[1][0] for item in bxs]
        text = "\n".join(lines)
        
        if return_orientation:
            # Kiểm tra xem chữ trong ảnh có bị nằm dọc không (ví dụ do xoay 90 độ)
            # Nếu hộp thoại chữ (box) có chiều cao lớn hơn chiều rộng -> Chữ dọc
            vertical_count = 0
            for box, _ in bxs:
                pts = box
                w = ((pts[0][0] - pts[1][0])**2 + (pts[0][1] - pts[1][1])**2)**0.5
                h = ((pts[0][0] - pts[3][0])**2 + (pts[0][1] - pts[3][1])**2)**0.5
                if h > w * 1.5: # Chiều cao gấp 1.5 lần chiều rộng -> Dọc
                    vertical_count += 1
            
            is_vertical = vertical_count > len(bxs) * 0.5 # Nếu quá nửa số dòng chữ là dọc
            return text, is_vertical
            
        return text
    except Exception as e:
        print(f"Lỗi khi chạy OCR: {e}")
        return ("", False) if return_orientation else ""
