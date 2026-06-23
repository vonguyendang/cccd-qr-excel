import sys
import os
import time
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from wizard.main import process_single_image

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
print("Starting process_single_image...")
t0 = time.time()
res, logs = process_single_image(img_path)
print(f"Finished in {time.time() - t0}s")
print(res)
