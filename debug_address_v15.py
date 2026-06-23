import os
import cv2
import glob
import sys
import re
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from vietocr_engine import extract_text_from_image

def count_location_tokens(line_lower):
    location_tokens = ["số", "phường", "xã", "tp", "tỉnh", "ấp", "áp", "thôn", "đường", "quận", "huyện", "khu phố"]
    count = 0
    for token in location_tokens:
        if re.search(r'\b' + token + r'\b', line_lower):
            count += 1
    return count

def is_metadata_line(line_lower):
    bad_tokens = ["giới tính", "quốc tịch", "sex", "nationality", "expiry", 
                  "giá trị đến", "ngày cấp", "date of issue", "date of birth", 
                  "place of origin", "khai sinh", "đặc điểm nhận dạng", "ngón trỏ", "cục trưởng", "họ và tên", "full name", "quê quán", "ngày sinh"]
    return any(token in line_lower for token in bad_tokens)

def score_address_line(line):
    score = 0
    line_lower = line.lower()
    
    # 1. Dấu phẩy (đặc trưng địa chỉ)
    comma_count = line.count(',')
    score += min(comma_count * 5, 15)
    
    # 2. Token địa danh
    score += count_location_tokens(line_lower) * 3
            
    # 3. Điểm trừ cực mạnh (từ rác hoặc thông tin cột bên trái/phải)
    if is_metadata_line(line_lower):
        score -= 10
            
    # 4. Định dạng ngày tháng
    if re.search(r'\b\d{2}/\d{2}/\d{4}\b', line):
        score -= 5
        
    # 5. Noise ngắn
    noise_tokens = ["ngl", "ngi", "substates", "dater"]
    for token in noise_tokens:
        if re.search(r'\b' + token + r'\b', line_lower):
            score -= 2
            
    return score

def extract_address_v15(image):
    h, w = image.shape[:2]
    
    text, bxs = extract_text_from_image(image, return_boxes=True)
    if not bxs:
        return text, "", "Fallback (Không có text OCR)", {}
        
    zone_boxes = []
    for box_points, (line_text, conf) in bxs:
        cx = sum(p[0] for p in box_points) / 4.0
        cy = sum(p[1] for p in box_points) / 4.0
        if len(line_text.strip()) >= 2:
            zone_boxes.append({
                'text': line_text,
                'cx': cx,
                'cy': cy,
                'box': box_points
            })
            
    # Tìm mỏ neo (Anchor)
    anchor_idx = -1
    anchor_text = ""
    for i, item in enumerate(zone_boxes):
        txt_lower = item['text'].lower()
        if "thường trú" in txt_lower or "cư trú" in txt_lower or "residence" in txt_lower:
            anchor_idx = i
            anchor_text = item['text']
            break
            
    if anchor_idx == -1:
        return text, "", "Fallback (Không tìm thấy anchor 'thường trú')", {}
        
    # Xử lý dòng Anchor
    valid_lines = []
    total_score = 10 
    loc_tokens_count = 0
    comma_count = 0
    
    part_after = anchor_text
    match = re.search(r'(?i)(residence|thường trú|cư trú|thuong tru)[^\w]*', part_after)
    if match:
        part_after = part_after[match.end():].strip()
    part_after = re.sub(r'(?i)^([:;\-I\|]|\bplace\b|\bof\b|\bresidence\b|\bofresidence\b|\borigin\b|\bquê\b|\bquán\b|\s)*', '', part_after)
    part_after = re.sub(r'(?i)\b(disconterping|disconters|disconting|disconning|nterting)\b', '', part_after).strip()
    
    if len(part_after) > 2:
        if not is_metadata_line(part_after.lower()):
            sc = score_address_line(part_after)
            if sc >= 0:
                valid_lines.append(part_after)
                total_score += sc
                loc_tokens_count += count_location_tokens(part_after.lower())
                comma_count += part_after.count(',')
                
    # Duyệt tối đa 3 dòng tiếp theo nằm gần anchor
    anchor_item = zone_boxes[anchor_idx]
    anchor_cx, anchor_cy = anchor_item['cx'], anchor_item['cy']
    
    # Tính chiều cao của box anchor
    min_y = min(p[1] for p in anchor_item['box'])
    max_y = max(p[1] for p in anchor_item['box'])
    anchor_h = max(max_y - min_y, 10.0) # Tránh chia cho 0
    
    candidate_lines = []
    
    lines_added = 0
    for i in range(anchor_idx + 1, len(zone_boxes)):
        if lines_added >= 3:
            break
            
        item = zone_boxes[i]
        
        # Lọc không gian: Dòng phải nằm đủ gần mỏ neo theo trục dọc (Y)
        # Không dùng khoảng cách ngang (X) vì dòng chữ dài ngắn khác nhau làm lệch tâm rất nhiều
        dist_y = abs(item['cy'] - anchor_cy)
        if dist_y > 6.0 * anchor_h:
            continue
            
        txt_lower = item['text'].lower()
        
        # Nhận diện dòng rác để ngắt mạch (tránh quét nhầm họ tên nếu ảnh bị ngược)
        break_tokens = ["giới tính", "quốc tịch", "sex", "nationality", "ngày cấp", "date of issue", "date of birth", "place of origin", "khai sinh", "đặc điểm nhận dạng", "ngón trỏ", "cục trưởng", "họ và tên", "full name", "quê quán", "ngày sinh", "số cccd", "identity"]
        if any(token in txt_lower for token in break_tokens):
            break
            
        # Nhận diện dòng ngày hết hạn xen ngang trên thẻ mới
        ignore_tokens = ["giá trị đến"]
        if any(token in txt_lower for token in ignore_tokens):
            continue
            
        candidate_lines.append(item['text'])
        # Xóa các từ rác tiếng Anh thường xuyên dính vào
        txt_clean = re.sub(r'(?i)\b(disconterping|disconters|disconting|disconning|nterting|date|of|dale)\b', '', item['text']).strip()
        txt_clean = re.sub(r',\s*,', ',', txt_clean)
        
        sc = score_address_line(txt_clean)
        if sc >= 0:
            valid_lines.append(txt_clean)
            total_score += sc
            loc_tokens_count += count_location_tokens(item['text'].lower())
            comma_count += item['text'].count(',')
            lines_added += 1
                
    address_str = ", ".join(valid_lines)
    
    # Áp dụng logic lọc thông minh: Xóa luôn cụm giữa 2 dấu phẩy nếu chứa rác tiếng Anh đặc thù
    # Vì Tiếng Việt không bao giờ có vần kết thúc bằng f, s, r, l, hoặc từ nguyên âm ghép như dale, date
    bad_subs = ["pir", "dis", "ter", "of", "date", "dale"]
    parts = address_str.split(',')
    clean_parts = []
    for p in parts:
        if not any(bad in p.lower() for bad in bad_subs):
            clean_parts.append(p.strip())
            
    address_str = ", ".join(filter(bool, clean_parts))
    
    address_str = re.sub(r',\s*,', ',', address_str).strip(', ')
    
    # Log string format
    log_info = {
        "raw_anchor": anchor_text,
        "candidate_lines": candidate_lines,
        "total_score": total_score,
        "final_address": address_str,
    }
    
    # Điều kiện Pass
    if total_score < 10:
        return text, address_str, f"Fallback (Điểm quá thấp: {total_score})", log_info
        
    if comma_count < 1 and loc_tokens_count < 1:
        return text, address_str, f"Fallback (Thiếu dấu phẩy và từ địa danh)", log_info
        
    if len(address_str) < 10:
        return text, address_str, "Fallback (Chuỗi địa chỉ quá ngắn)", log_info
        
    return text, address_str, f"Pass", log_info


if __name__ == "__main__":
    img_dir = "/Users/dangvo/Projects/cccd-qr-excel/samples"
    images = glob.glob(os.path.join(img_dir, "*.[jJ][pP][gG]"))
    
    for img_path in sorted(images):
        print(f"\n{'='*50}\nProcessing: {os.path.basename(img_path)}")
        img = cv2.imread(img_path)
        if img is None: continue
        
        raw_text, address_v15, status, log_info = extract_address_v15(img)
        
        if "Fallback" in status:
            print(f"[Status]          {status}")
        else:
            print(f"[Raw Anchor]      {log_info['raw_anchor']}")
            print(f"[Candidate Lines] {log_info['candidate_lines']}")
            print(f"[Total Score]     {log_info['total_score']}")
            print(f"[Final Address]   {log_info['final_address']}")
            print(f"[Status]          {status}")
