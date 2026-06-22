import sys, os, cv2, time
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from wizard.main import extract_qr_data, align_card

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
print("Loading image...")
_, _, _, img, rotated = extract_qr_data(img_path)
img_to_ocr = rotated if rotated is not None else img
card_img, _, _ = align_card(img_to_ocr)

hr, wr = card_img.shape[:2]
if max(wr, hr) > 1500:
    scale = 1500 / max(wr, hr)
    card_img = cv2.resize(card_img, (int(wr * scale), int(hr * scale)))
    hr, wr = card_img.shape[:2]

best_back_rotated_img = card_img
bottom_crop = best_back_rotated_img[int(hr * 0.65):hr, :]

gray_bottom = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2GRAY)
hr_b, wr_b = gray_bottom.shape[:2]
resized_b = cv2.resize(gray_bottom, (wr_b*2, hr_b*2), interpolation=cv2.INTER_CUBIC)
bordered = cv2.copyMakeBorder(resized_b, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255])

import pytesseract
custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'

thresh_levels = [
    ("otsu",  lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]),
    ("light", lambda img: cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)[1]),
    ("strong",lambda img: cv2.threshold(img, 160, 255, cv2.THRESH_BINARY)[1]),
]

for level_name, thresh_fn in thresh_levels:
    thresh_tess = thresh_fn(bordered)
    print(f"Running tesseract for level: {level_name}...")
    t0 = time.time()
    tess_text = pytesseract.image_to_string(thresh_tess, config=custom_config)
    print(f"Time for {level_name}: {time.time() - t0}s")
    print(f"Result: {tess_text[:100]}")
