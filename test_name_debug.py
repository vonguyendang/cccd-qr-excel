import sys
import os
import cv2

project_dir = '/Users/dangvo/Projects/cccd-qr-excel'
sys.path.append(project_dir)

from wizard.main import extract_ocr_data
from vietocr_engine import extract_text_from_image

def test_images():
    img_dir = "/Users/dangvo/DATA/THAOPHAM/OG_CCCD_part2_exports/review"
    test_files = ["3.jpg", "4.jpg"]
    
    for f in test_files:
        path = os.path.join(img_dir, f)
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        print(f"\\n--- Processing {f} ---")
        img = cv2.imread(path)
        
        # Raw text from OCR
        try:
            raw_text = extract_text_from_image(img)
            print("RAW TEXT:")
            print(raw_text)
            print("-" * 20)
        except Exception as e:
            print(f"Error raw OCR: {e}")
            
        # Parse data
        data, notes, rotated = extract_ocr_data(path)
        print("PARSED DATA:")
        print(data)

if __name__ == "__main__":
    test_images()
