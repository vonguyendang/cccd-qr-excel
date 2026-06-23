import sys
import time
import os

sys.path.insert(0, os.path.abspath('wizard'))
sys.path.insert(0, os.path.abspath('.'))

from wizard.main import extract_qr_data
import cv2

print("Testing 158.jpg")
t0 = time.time()
print(extract_qr_data('/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg')[:3])
print(f"Finished 158 in {time.time()-t0:.2f}s")

print("Testing 123.jpg")
t0 = time.time()
print(extract_qr_data('/Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/123.jpg')[:3])
print(f"Finished 123 in {time.time()-t0:.2f}s")
