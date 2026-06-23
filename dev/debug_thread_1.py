import sys
import time
import os
import concurrent.futures

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

sys.path.insert(0, os.path.abspath('wizard'))
sys.path.insert(0, os.path.abspath('deepdoc_vietocr'))
sys.path.insert(0, os.path.abspath('.'))

import torch
torch.set_num_threads(1)

import cv2
from module.ocr import OCR

print("Loading OCR in main thread...")
ocr = OCR()

print("Loading image...")
img = cv2.imread('/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg')

def run_ocr_in_worker():
    print("Running OCR in worker thread...")
    t0 = time.time()
    bxs = ocr(img, 0)
    print(f"Finished in {time.time()-t0:.2f}s")
    print(f"Number of boxes: {len(bxs) if bxs else 0}")
    return True

print("Starting ThreadPool with 1 worker...")
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    f = executor.submit(run_ocr_in_worker)
    f.result()
