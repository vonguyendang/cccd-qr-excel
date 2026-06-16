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

# Singleton instance
_ocr_instance = None

def get_ocr_engine():
    global _ocr_instance
    if _ocr_instance is None:
        print("Đang khởi tạo AI Model Deepdoc_VietOCR (lần đầu sẽ mất vài giây)...")
        _ocr_instance = OCR()
    return _ocr_instance

def extract_text_from_image(img):
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
            return ""
        # bxs là list các tuple: (box, (text, score))
        lines = [item[1][0] for item in bxs]
        return "\n".join(lines)
    except Exception as e:
        print(f"Lỗi khi chạy OCR: {e}")
        return ""
