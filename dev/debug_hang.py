import sys
import time
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

sys.path.insert(0, os.path.abspath('wizard'))
sys.path.insert(0, os.path.abspath('.'))

from wizard.main import extract_qr_data, extract_ocr_data
import cv2

def test_image(img_path):
    print(f"Testing {os.path.basename(img_path)}...")
    t0 = time.time()
    
    print("  -> extract_qr_data starting...")
    qr_string, engine, err, img, qr_rotated_img = extract_qr_data(img_path)
    print(f"  <- extract_qr_data finished in {time.time()-t0:.2f}s. Result: {qr_string}")
    
    if not qr_string:
        print("  -> extract_ocr_data starting...")
        t1 = time.time()
        ocr_data, ocr_note, rotated_img = extract_ocr_data(img)
        print(f"  <- extract_ocr_data finished in {time.time()-t1:.2f}s. Result: {ocr_data}")

test_image('/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg')
test_image('/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/123.jpg')
