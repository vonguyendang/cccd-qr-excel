import sys, os, cv2, time
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from vietocr_engine import extract_text_from_image
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

top_crop = card_img[0:int(hr * 0.70), :]

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
lab = cv2.cvtColor(top_crop, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
l2 = clahe.apply(l)
img_contrast = cv2.cvtColor(cv2.merge((l2,a,b)), cv2.COLOR_LAB2BGR)

print("Running OCR on contrast image...")
t0 = time.time()
text = extract_text_from_image(img_contrast)
print(f"Time: {time.time() - t0}s")
print(f"Length of text: {len(text)}")
print("First 500 chars:", text[:500])
