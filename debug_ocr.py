import sys
import os
import cv2

sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')
from vietocr_engine import extract_text_from_image
from wizard.main import parse_ocr_text, clean_address_string, extract_qr_data, clean_name_string

images = [
    '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/283.jpg',
    '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
]

for img_path in images:
    print(f"\n--- DEBUG: {os.path.basename(img_path)} ---")
    qr_data, engine, err, img, rotated = extract_qr_data(img_path)
    if rotated is not None:
        img_to_ocr = rotated
    else:
        img_to_ocr = img
        
    if img_to_ocr is None:
        print("Không đọc được ảnh")
        continue

    text = extract_text_from_image(img_to_ocr)
    print(">>> RAW TEXT:")
    print(text)
    print("----------------")
    
    parsed = parse_ocr_text(text)
    print(">>> PARSED DATA:")
    for k, v in parsed.items():
        if k not in ['Raw Text Upper', 'Raw Text']:
            print(f"{k}: {v}")
            
    print("\n>>> CLEANED DATA:")
    print("Cleaned Name:", clean_name_string(parsed.get('Họ tên', '')))
    print("Cleaned Address:", clean_address_string(parsed.get('Nơi thường trú gốc', '')))

