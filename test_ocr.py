import os
import sys
import time

def test_paddle(img_path):
    print("=== Testing PaddleOCR ===")
    start = time.time()
    try:
        from paddleocr import PaddleOCR
        # need to run only once to download and load model into memory
        ocr = PaddleOCR(use_angle_cls=True, lang='vi')
        result = ocr.ocr(img_path, cls=True)
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                print(line[1][0])
    except Exception as e:
        print("PaddleOCR failed:", e)
    print(f"PaddleOCR time: {time.time() - start:.2f}s\n")

def test_vietocr(img_path):
    print("=== Testing deepdoc_vietocr ===")
    start = time.time()
    try:
        # Import directly from the deepdoc_vietocr module
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deepdoc_vietocr'))
        from module.ocr import OCR
        from PIL import Image
        import numpy as np

        ocr = OCR()
        img = Image.open(img_path)
        bxs = ocr(np.array(img), 0)
        
        # Bxs structure: list of (box, text_result)
        # text_result is (text, score)
        for box, (text, score) in bxs:
            print(text)
            
    except Exception as e:
        print("deepdoc_vietocr failed:", e)
    print(f"deepdoc_vietocr time: {time.time() - start:.2f}s\n")

if __name__ == "__main__":
    img_path = "dummy_cccd.jpg"
    test_paddle(img_path)
    test_vietocr(img_path)
