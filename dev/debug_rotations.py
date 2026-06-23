import sys, cv2, time
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from wizard.main import extract_qr_data, align_card
from vietocr_engine import extract_text_from_image

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
_, _, _, img, rotated = extract_qr_data(img_path)
img_to_ocr = rotated if rotated is not None else img
card_img, _, _ = align_card(img_to_ocr)

rotations = [
    (None, "Không xoay"),
    (cv2.ROTATE_90_COUNTERCLOCKWISE, "Xoay trái 90 độ"),
    (cv2.ROTATE_90_CLOCKWISE, "Xoay phải 90 độ"),
    (cv2.ROTATE_180, "Xoay 180 độ")
]

for rot_code, rot_name in rotations:
    print(f"Testing rotation: {rot_name}")
    rotated = card_img if rot_code is None else cv2.rotate(card_img, rot_code)
    hr, wr = rotated.shape[:2]
    bottom_crop = rotated[int(hr * 0.65):hr, :]
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l2 = clahe.apply(l)
    mrz_contrast = cv2.cvtColor(cv2.merge((l2,a,b)), cv2.COLOR_LAB2BGR)
    
    t0 = time.time()
    text_bottom = extract_text_from_image(mrz_contrast)
    print(f"Time for {rot_name}: {time.time() - t0}s")
    upper_text = text_bottom.upper()
    print("Extracted text upper:", upper_text[:100])
    
    score = 0
    if 'IDVNM' in upper_text: score += 500
    if 'VNM' in upper_text: score += 200
    print("Score:", score)
    if score >= 700:
        print("BREAK!")
        break
