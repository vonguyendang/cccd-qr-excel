import os
import sys
import numpy as np
from PIL import Image

# Giới hạn số luồng của OpenMP/MKL để tránh thread explosion khi chạy ThreadPoolExecutor
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# Thêm thư mục deepdoc_vietocr vào PYTHONPATH
base_dir = os.path.dirname(os.path.abspath(__file__))
deepdoc_path = os.path.join(base_dir, 'deepdoc_vietocr')
if deepdoc_path not in sys.path:
    sys.path.insert(0, deepdoc_path)

from module.ocr import OCR

import threading
import torch

_ocr_engine = None
_ocr_lock = threading.Lock()

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            torch.set_num_threads(1)
        except Exception:
            pass
        _ocr_engine = OCR()
    return _ocr_engine

def extract_text_from_image(img, return_orientation=False, fast_mode=False, return_boxes=False):
    """
    Trích xuất text tiếng Việt từ ảnh (numpy array hoặc PIL Image)
    Nếu fast_mode=True, chỉ giữ lại 5 box chữ to nhất để nhận diện hướng cho nhanh (x15 tốc độ)
    """
    if isinstance(img, Image.Image):
        img_array = np.array(img.convert('RGB'))
    else:
        img_array = img
        
    try:
        # Sử dụng threading.Lock() để đảm bảo chỉ 1 luồng được chạy OCR tại 1 thời điểm.
        # Ngăn chặn lỗi deadlock của PyTorch/ONNX khi chạy song song.
        with _ocr_lock:
            engine = get_ocr_engine()
            max_boxes = 8 if fast_mode else 80
            bxs = engine(img_array, 0, max_boxes=max_boxes)
        
        if not bxs:
            if return_boxes:
                return ("", [], False) if return_orientation else ("", [])
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
            if return_boxes:
                return text, bxs, is_vertical
            return text, is_vertical
            
        if return_boxes:
            return text, bxs
        return text
    except Exception as e:
        print(f"Lỗi khi chạy OCR: {e}")
        if return_boxes:
            return ("", [], False) if return_orientation else ("", [])
        return ("", False) if return_orientation else ""
