import sys, cv2, time
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from wizard.main import extract_qr_data
from vietocr_engine import extract_text_from_image

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
_, _, _, img, rotated = extract_qr_data(img_path)
img_to_ocr = rotated if rotated is not None else img

front_rotations = [
    (None, "Không xoay"),
    (cv2.ROTATE_90_COUNTERCLOCKWISE, "Xoay trái 90 độ"),
    (cv2.ROTATE_90_CLOCKWISE, "Xoay phải 90 độ"),
    (cv2.ROTATE_180, "Xoay 180 độ")
]

print("Running fallback loop on full image...")
total_t = time.time()
for rot_code, rot_name in front_rotations:
    print(f"Testing fallback rotation: {rot_name}")
    rotated = img_to_ocr if rot_code is None else cv2.rotate(img_to_ocr, rot_code)
    t0 = time.time()
    text_rot = extract_text_from_image(rotated)
    print(f"Time for {rot_name}: {time.time() - t0}s")
    
print(f"Total fallback loop time: {time.time() - total_t}s")
