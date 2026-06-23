import sys
import os
import cv2

sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from vietocr_engine import extract_text_from_image
from wizard.main import parse_ocr_text, clean_address_string, extract_qr_data, clean_name_string, align_card

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'

print(f"\n--- DEBUG 2: {os.path.basename(img_path)} ---")
qr_data, engine, err, img, rotated = extract_qr_data(img_path)
if rotated is not None:
    img_to_ocr = rotated
else:
    img_to_ocr = img
    
if img_to_ocr is None:
    print("Không đọc được ảnh")
    sys.exit(1)

print("Running align_card...")
card_img, debug_detect_img, align_method = align_card(img_to_ocr)
print(f"align_method: {align_method}, card_img shape: {card_img.shape}")

card_h, card_w = card_img.shape[:2]
max_dim = 1500
if max(card_w, card_h) > max_dim:
    scale = max_dim / max(card_w, card_h)
    card_img = cv2.resize(card_img, (int(card_w * scale), int(card_h * scale)), interpolation=cv2.INTER_AREA)
    print(f"Resized card_img shape: {card_img.shape}")

print("Running extract_text_from_image...")
try:
    text = extract_text_from_image(card_img)
    print(">>> RAW TEXT:")
    print(text)
except Exception as e:
    print("Error in extract:", e)

