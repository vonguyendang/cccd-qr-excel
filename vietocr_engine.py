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

# Sử dụng ProcessPoolExecutor để chạy OCR ở một process hoàn toàn độc lập,
# tránh 100% lỗi deadlock của PyTorch/ONNX khi kết hợp với ThreadPoolExecutor trên MacOS.
import threading
import concurrent.futures
import multiprocessing

_process_pool = None
_pool_lock = threading.Lock()

def _run_ocr_in_process(img_array, device_id):
    """
    Hàm này chạy hoàn toàn trong một Worker Process tách biệt.
    Không bao giờ đụng độ với GIL hoặc ThreadPool của Process chính.
    """
    import os, sys
    in_colab = 'COLAB_RELEASE_TAG' in os.environ
    if in_colab:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
    import torch
    try:
        torch.set_num_threads(1)
    except:
        pass
        
    from module.ocr import OCR
    global _local_ocr
    if '_local_ocr' not in globals():
        _local_ocr = OCR()
        
    bxs = _local_ocr(img_array, device_id)
    return bxs

def get_ocr_engine():
    # Hàm này không còn cần thiết khởi tạo model ở main process nữa
    # vì model sẽ được khởi tạo an toàn bên trong Worker Process.
    pass

def extract_text_from_image(img, return_orientation=False):
    """
    Trích xuất text tiếng Việt từ ảnh (numpy array hoặc PIL Image)
    """
    global _process_pool
    
    if isinstance(img, Image.Image):
        img_array = np.array(img.convert('RGB'))
    else:
        img_array = img
        
    try:
        with _pool_lock:
            if _process_pool is None:
                ctx = multiprocessing.get_context('spawn')
                _process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=ctx)
                
        # Gửi ảnh sang Process phụ để chạy AI, chờ nhận kết quả
        future = _process_pool.submit(_run_ocr_in_process, img_array, 0)
        bxs = future.result(timeout=120) # Thêm timeout 120s chống kẹt vĩnh viễn
        
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
