import sys
import time
import os
import concurrent.futures

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

sys.path.insert(0, os.path.abspath('wizard'))
sys.path.insert(0, os.path.abspath('.'))

import torch
torch.set_num_threads(1)

from wizard.main import extract_qr_data, extract_ocr_data

def process_img(img_path):
    print(f"[{img_path}] Starting QR...")
    t0 = time.time()
    qr_res = extract_qr_data(img_path)
    print(f"[{img_path}] QR done in {time.time()-t0:.2f}s")
    
    img = qr_res[3]
    if img is not None:
        print(f"[{img_path}] Starting OCR...")
        t1 = time.time()
        ocr_res = extract_ocr_data(img)
        print(f"[{img_path}] OCR done in {time.time()-t1:.2f}s")
    return True

paths = [
    '/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg',
    '/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/123.jpg'
]

print("Starting ThreadPool...")
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_img, p) for p in paths]
    for f in concurrent.futures.as_completed(futures):
        print(f.result())
