import os
import cv2
import numpy as np
import glob
import logging
import sys

# Thêm path để import vietocr_engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from vietocr_engine import extract_text_from_image

# Setup logging
if not os.path.exists("debug_output"):
    os.makedirs("debug_output")
logging.basicConfig(filename='debug_flow_layout.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s', filemode='w')

def LOG(msg):
    logging.info(msg)
    print(msg)

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts, dst_w=856, dst_h=540):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    is_vertical = maxHeight > maxWidth
    
    if is_vertical:
        dst = np.array([
            [0, 0],
            [dst_h - 1, 0],
            [dst_h - 1, dst_w - 1],
            [0, dst_w - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (dst_h, dst_w))
        # Thử xoay 90 độ ngược chiều kim đồng hồ để nằm ngang
        warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if warped.shape[1] != dst_w:
            warped = cv2.resize(warped, (dst_w, dst_h))
    else:
        dst = np.array([
            [0, 0],
            [dst_w - 1, 0],
            [dst_w - 1, dst_h - 1],
            [0, dst_h - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (dst_w, dst_h))

    return warped, is_vertical

def detect_card(image_path, out_prefix):
    img = cv2.imread(image_path)
    if img is None:
        return None, False, "Load failed"
    
    cv2.imwrite(f"{out_prefix}_original.jpg", img)
    orig = img.copy()
    h, w = img.shape[:2]
    
    # Giảm nhiễu và làm nổi bật mép thẻ
    ratio = h / 800.0
    proc_img = cv2.resize(img, (int(w / ratio), 800))
    gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Canny Edge detection
    edged = cv2.Canny(gray, 30, 150)
    cv2.imwrite(f"{out_prefix}_edged.jpg", edged)

    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

    screenCnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break
            
    if screenCnt is None:
        return img, False, "Contour not found"

    overlay = proc_img.copy()
    cv2.drawContours(overlay, [screenCnt], -1, (0, 255, 0), 2)
    cv2.imwrite(f"{out_prefix}_contour_overlay.jpg", overlay)

    # Scale points back to original image size
    screenCnt = screenCnt.reshape(4, 2) * ratio
    
    warped, is_vertical = four_point_transform(orig, screenCnt, dst_w=856, dst_h=540)
    cv2.imwrite(f"{out_prefix}_warped.jpg", warped)
    
    return warped, is_vertical, "Success"

def process_image(img_path):
    filename = os.path.basename(img_path)
    base_name = os.path.splitext(filename)[0]
    out_prefix = f"debug_output/{base_name}"
    
    LOG(f"\n--- Processing {filename} ---")
    
    warped, is_vertical, msg = detect_card(img_path, out_prefix)
    
    if msg != "Success":
        LOG(f"[Layout-First] fallback_candidate=true, Reason: {msg}")
        return False
        
    LOG(f"[Layout-First] Contour found: 4 points. Warp successful. Rotation detected: {is_vertical}")
    
    # Kích thước chuẩn là 856x540
    # Cắt vùng địa chỉ: Nửa dưới bên phải. Tránh vùng chân dung ở dưới trái.
    h, w = warped.shape[:2]
    crop_x1 = int(w * 0.30)
    crop_y1 = int(h * 0.50)
    crop_x2 = int(w * 0.98)
    crop_y2 = int(h * 0.95)
    
    address_crop = warped[crop_y1:crop_y2, crop_x1:crop_x2]
    cv2.imwrite(f"{out_prefix}_address_crop.jpg", address_crop)
    LOG(f"[Layout-First] Crop box: ({crop_x1}, {crop_y1}) to ({crop_x2}, {crop_y2})")
    
    # Chạy OCR
    ocr_text = extract_text_from_image(address_crop, fast_mode=False)
    LOG(f"[Layout-First] OCR Text:\n{ocr_text}")
    
    # Đánh giá kết quả (PASS nếu tìm thấy từ khóa mỏ neo)
    text_lower = ocr_text.lower()
    if "thường trú" in text_lower or "cư trú" in text_lower or "residence" in text_lower:
        LOG("[Result] PASS")
        return True
    else:
        LOG("[Result] FAIL (No anchor found in OCR text. Fallback candidate.)")
        return False

if __name__ == "__main__":
    img_dir = "/Users/dangvo/DATA/THAOPHAM/CCCD_23062026_to9h00"
    if not os.path.exists(img_dir):
        LOG(f"Error: Directory {img_dir} does not exist.")
        sys.exit(1)
        
    images = glob.glob(os.path.join(img_dir, "*.[jJ][pP][gG]"))
    images += glob.glob(os.path.join(img_dir, "*.[pP][nN][gG]"))
    
    results = {}
    for img_path in sorted(images):
        success = process_image(img_path)
        results[os.path.basename(img_path)] = success
        
    LOG("\n=== SUMMARY ===")
    pass_count = 0
    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        LOG(f"{name}: {status}")
        if success: pass_count += 1
        
    LOG(f"Total: {len(images)}, Pass: {pass_count}, Fail: {len(images) - pass_count}")
