import os
import sys
import glob
import cv2
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol
import openpyxl
from openpyxl.styles import Font
import requests
import datetime
import pillow_heif
import numpy as np
from PIL import Image
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vietocr_engine import extract_text_from_image
import re
import concurrent.futures
import zipfile

# Global AI Models
detector = None

def init_models():
    global detector
    model_paths = [
        'models/detect.prototxt', 'models/detect.caffemodel',
        'models/sr.prototxt', 'models/sr.caffemodel'
    ]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_paths = [os.path.join(base_dir, p) for p in model_paths]
    
    if all(os.path.exists(p) for p in abs_paths):
        try:
            detector = cv2.wechat_qrcode_WeChatQRCode(*abs_paths)
            print("Đã tải thành công mô hình WeChat QRCode siêu cấp.")
        except Exception as e:
            print(f"Lỗi khởi tạo WeChat QRCode: {e}")
    else:
        print("Cảnh báo: Không tìm thấy file model WeChat QRCode. Khả năng quét ảnh mờ sẽ bị giảm.")
def format_date(date_str):
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[0:2]}/{date_str[2:4]}/{date_str[4:8]}"

def get_place_of_issue(qr_data):
    if not qr_data:
        return ""
    fields = qr_data.split('|')
    if len(fields) == 7:
        return "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    elif len(fields) >= 10:
        return "BỘ CÔNG AN"
    return "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"

def get_card_type(qr_data):
    if not qr_data:
        return ""
    fields = qr_data.split('|')
    if len(fields) == 7:
        return "Căn cước công dân"
    elif len(fields) >= 10:
        return "Căn cước"
    return "Không xác định"

def calculate_expiry_date(dob_str):
    if not dob_str or len(dob_str) != 10:
        return ""
    try:
        day, month, year = dob_str.split('/')
        year = int(year)
        current_year = datetime.datetime.now().year
        for age in [14, 25, 40, 60]:
            expiry_year = year + age
            if expiry_year > current_year:
                return f"{day}/{month}/{expiry_year}"
        return "Không thời hạn"
    except:
        return ""

def extract_qr_data(image_path):
    try:
        # Read the image
        if image_path.lower().endswith('.heic'):
            heif_file = pillow_heif.read_heif(image_path)
            img_pil = Image.frombytes(
                heif_file.mode, 
                heif_file.size, 
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
            # Convert to numpy array and BGR for OpenCV
            img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        else:
            img = cv2.imread(image_path)
            
        if img is None:
            return None, None, "Lỗi đọc file ảnh", None

        import re
        def _try_scan(scan_img):
            # 1. zxingcpp
            try:
                import zxingcpp
                res = zxingcpp.read_barcode(scan_img)
                if res and res.text:
                    if not re.search(r'[^\x00-\x7FÀ-ỹ\s\|\:\-/\.]', res.text):
                        pos = res.position
                        cx = (pos.top_left.x + pos.bottom_right.x) / 2
                        cy = (pos.top_left.y + pos.bottom_right.y) / 2
                        return res.text, "zxing-cpp", (cx, cy)
            except Exception:
                pass

            # 2. pyzbar
            decoded_objects = decode(scan_img, symbols=[ZBarSymbol.QRCODE])
            if not decoded_objects:
                gray = cv2.cvtColor(scan_img, cv2.COLOR_BGR2GRAY)
                decoded_objects = decode(gray, symbols=[ZBarSymbol.QRCODE])
                if not decoded_objects:
                    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                    decoded_objects = decode(thresh, symbols=[ZBarSymbol.QRCODE])

            if decoded_objects:
                obj = decoded_objects[0]
                txt = obj.data.decode('utf-8')
                if '|' in txt and len(txt.split('|')) >= 6:
                    if not re.search(r'[^\x00-\x7FÀ-ỹ\s\|\:\-/\.]', txt):
                        rect = obj.rect
                        cx = rect.left + rect.width / 2
                        cy = rect.top + rect.height / 2
                        return txt, "pyzbar", (cx, cy)

            # 3. wechat_qrcode
            global detector
            if detector:
                try:
                    res, points = detector.detectAndDecode(scan_img)
                    if res and len(res) > 0:
                        txt = res[0]
                        if '|' in txt and len(txt.split('|')) >= 6:
                            if not re.search(r'[^\x00-\x7FÀ-ỹ\s\|\:\-/\.]', txt):
                                pts = points[0]
                                cx = sum(p[0] for p in pts) / 4
                                cy = sum(p[1] for p in pts) / 4
                                return txt, "WeChat QRCode", (cx, cy)
                except Exception:
                    pass
            
            return None, None, None

        # 1. Quét toàn bộ ảnh
        qr_data, engine, center = _try_scan(img)
        
        # 2. Quét góc phần tư phía trên bên phải (CCCD) nếu toàn bộ ảnh thất bại
        if not qr_data:
            h, w = img.shape[:2]
            crop = img[0:int(h/2), int(w/2):w]
            qr_data, engine, crop_center = _try_scan(crop)
            if qr_data and crop_center:
                center = (crop_center[0] + w/2, crop_center[1])

        rotated_img = None
        if qr_data and center:
            cx, cy = center
            h, w = img.shape[:2]
            
            # Lấy vector từ tâm ảnh đến QR
            dx = cx - w/2
            dy = cy - h/2
            
            # Chỉ xoay nếu QR nằm lệch rõ ràng khỏi tâm (tránh nhiễu)
            if max(abs(dx), abs(dy)) > min(w, h) * 0.05:
                if abs(dx) > abs(dy):
                    # QR nằm thiên về hai bên trái/phải -> Thẻ đang nằm ngang
                    if dx < 0:
                        # QR bên trái -> Thẻ bị lộn ngược 180 độ
                        rotated_img = cv2.rotate(img, cv2.ROTATE_180)
                    # Nếu dx > 0: QR bên phải -> Thẻ đúng chiều, không cần xoay
                else:
                    # QR nằm thiên về trên/dưới -> Thẻ đang nằm dọc
                    if dy < 0:
                        # QR ở trên -> Xoay 90 độ cùng chiều kim đồng hồ
                        rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    else:
                        # QR ở dưới -> Xoay 90 độ ngược chiều kim đồng hồ
                        rotated_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        if qr_data:
            return qr_data, engine, None, img, rotated_img
        else:
            return None, None, "QR không đọc được", img, None

    except Exception as e:
        return None, None, f"Lỗi xử lý ảnh: {str(e)}", None, None


def parse_ocr_text(text):
                data = {
                    'CCCD': '', 'CMND': '', 'Họ tên': '', 'Ngày sinh': '',
                    'Giới tính': '', 'Nơi thường trú gốc': '', 'Ngày cấp CCCD': '',
                    'OCR Side': ''
                }

                if not text.strip():
                    return data, "Ảnh không thể nhận diện được chữ"

                text_upper = text.upper()

                # ---------------------------------------------------------
                # 1. NHẬN DIỆN MẶT THẺ (FRONT / BACK)
                # Dựa vào các từ khóa đặc trưng xuất hiện trên từng mặt thẻ
                # ---------------------------------------------------------
                if "<<" in text_upper or "IDVNM" in text_upper or "ĐẶC ĐIỂM NHẬN DẠNG" in text_upper or "NGÓN TRỎ" in text_upper or "CỤC TRƯỞNG" in text_upper:
                    data['OCR Side'] = 'Back'
                # Các từ khóa đặc trưng của Mặt Trước
                elif "CĂN CƯỚC" in text_upper or "CẦN CƯỚC" in text_upper or "CÔNG DÂN" in text_upper or "ĐỘC LẬP" in text_upper or "TỰ DO" in text_upper or "HỌ VÀ TÊN" in text_upper:
                    data['OCR Side'] = 'Front'

                # ---------------------------------------------------------
                # 2. TRÍCH XUẤT SỐ CCCD
                # ---------------------------------------------------------
                # Bước 2.1: Ưu tiên tìm chuỗi 12 số đứng độc lập bắt đầu bằng số 0 (có thể bị OCR chèn khoảng trắng)
                text_numbers = text_upper.replace('O', '0')
                cccd_match = re.search(r'\b(0[\d\s]{11,15})\b', text_numbers)
                if cccd_match:
                    val = cccd_match.group(1).replace(' ', '')
                    if len(val) >= 12:
                        data['CCCD'] = val[:12]

                if not data['CCCD']:
                    # Bước 2.2: Lấy từ mã MRZ ở mặt sau (Mã MRZ là chuỗi ký tự ở đáy mặt sau thẻ)
                    # Tại Việt Nam, thẻ CCCD áp dụng chuẩn ICAO chia số CCCD thành 2 đoạn trong mã MRZ:
                    # Ví dụ MRZ có chuỗi: VNM0960051566086... 
                    # -> Phân tích: 096005156 (9 số cuối của CCCD) + 6 (Mã kiểm tra) + 086 (3 số đầu của CCCD)
                    # Sửa lỗi OCR: Chữ 'O' thường bị AI đọc nhầm thay vì số '0' -> replace 'O' bằng '0'
                    text_mrz = text_upper.replace('O', '0') 
                    # Fallback cho chuẩn MRZ cũ/khác có chứa trực tiếp chuỗi 12 số CCCD liền kề dấu '<'
                    mrz_12_match = re.search(r'(\d{12})<', text_mrz)
                    if mrz_12_match:
                        data['CCCD'] = mrz_12_match.group(1)
                    else:
                        mrz_match = re.search(r'VNM(\d{9})\d(\d{3})', text_mrz)
                        if mrz_match:
                            # Lắp ráp lại thành CCCD hoàn chỉnh (3 số đầu + 9 số cuối)
                            data['CCCD'] = mrz_match.group(2) + mrz_match.group(1)
                        else:
                            # Bước 2.3: Chặn bắt cuối cùng (Fallback), quét tìm chuỗi 12 số liền nhau bắt đầu bằng số 0
                            # Dùng text_mrz để đảm bảo chữ 'O' đã được chuyển thành '0'
                            text_clean = text_mrz.replace(' ', '').replace('\n', '')
                            fallback_match = re.search(r'(0\d{11})', text_clean)
                            if fallback_match:
                                data['CCCD'] = fallback_match.group(1)
                all_dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)
    
                # ---------------------------------------------------------
                # 3. TRÍCH XUẤT GIỚI TÍNH (Thuật toán Fallback toàn cục)
                # Lưu ý: Sẽ bị ghi đè nếu lát nữa vòng lặp đọc được dòng chứa chữ "Giới tính" rõ ràng.
                # Logic: Đếm số từ 'nam' trong toàn văn bản, sau đó trừ đi chữ 'Việt Nam' (Quốc tịch)
                # ---------------------------------------------------------
                text_lower = text.lower()
                # Chỉ đếm giới tính rải rác nếu không phải mặt sau (vì mặt sau không có thông tin giới tính)
                if data['OCR Side'] != 'Back':
                    nam_count = len(re.findall(r'\bnam\b', text_lower))
                    vietnam_count = len(re.findall(r'việt nam|viet nam|hà nam|quảng nam|hải nam', text_lower))
                    if nam_count > vietnam_count:
                        data['Giới tính'] = 'Nam'
                    elif re.search(r'\bn[uưứữ][\s]*\b', text_lower) or re.search(r'\bnữ\b', text_lower):
                        data['Giới tính'] = 'Nữ'
        
                lines = [line.strip() for line in text.split('\n') if line.strip()]

                # ---------------------------------------------------------
                # 4. DUYỆT TỪNG DÒNG (VÉT THÔNG TIN: TÊN, ĐỊA CHỈ, NGÀY THÁNG)
                # OCR đọc ảnh từ trên xuống dưới, nên ta duyệt từng dòng để bắt từ khóa
                # ---------------------------------------------------------
                for i, line in enumerate(lines):
                    line_lower = line.lower()
    
                    # 1. Name
                    if "họ và tên" in line_lower or "họ chữ đệm và tên" in line_lower or "full name" in line_lower:
                        if ":" in line:
                            name_part = line.split(":", 1)[1].strip()
                            if name_part.isupper() and len(name_part) > 3:
                                data['Họ tên'] = name_part
                        if not data['Họ tên'] and i + 1 < len(lines):
                            next_line = lines[i+1].replace('|', '').strip()
                            if next_line.isupper() and len(next_line) > 3:
                                data['Họ tên'] = next_line
                
                    # 2. DOB
                    if "sinh" in line_lower or "birth" in line_lower:
                        for j in range(i, min(i+2, len(lines))):
                            m = re.search(r'\b\d{2}/\d{2}/\d{4}\b', lines[j])
                            if m:
                                data['Ngày sinh'] = m.group(0)
                                break
                
                    # --- BƯỚC 4.3: TRÍCH XUẤT ĐỊA CHỈ (NƠI THƯỜNG TRÚ/CƯ TRÚ) ---
                    if "nơi thường trú" in line_lower or "nơi cư trú" in line_lower or "residence" in line_lower:
                        addr_parts = []
                        if ":" in line:
                            addr_parts.append(line.split(":", 1)[1].strip())
        
                        # Quét các dòng tiếp theo để nối đuôi địa chỉ do địa chỉ thường rất dài và bị rớt dòng.
                        # Bỏ qua các dòng rác bị AI đọc đan xen vào (như 'giá trị đến', 'date') do layout 2 cột của thẻ.
                        # Ngắt ngay (break) nếu gặp 'nơi đăng ký khai sinh' (tránh gộp quê quán vào nơi ở của thẻ mới).
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].replace('|', '').strip()
                            next_lower = next_line.lower()
                            if "giá trị đến" in next_lower or "expiry" in next_lower or "date" in next_lower:
                                continue
                            if "khai sinh" in next_lower or "birth" in next_lower or "nơi cấp" in next_lower or "bộ công an" in next_lower or "cục cảnh sát" in next_lower:
                                break
                            if re.search(r'\b\d{2}/\d{2}/\d{4}\b', next_line):
                                continue
                            if len(next_line) > 3:
                                addr_parts.append(next_line)
                
                        addr = ", ".join(filter(bool, addr_parts))
                        data['Nơi thường trú gốc'] = re.sub(r',\s*,', ',', addr).lstrip(', ')
        
                    # --- BƯỚC 4.4: TRÍCH XUẤT GIỚI TÍNH (Chính xác từ dòng ghi Giới tính) ---
                    if "giới tính" in line_lower or "sex" in line_lower:
                        if "nữ" in line_lower or "nư" in line_lower or "nu " in line_lower:
                            data['Giới tính'] = 'Nữ'
                        elif "nam" in line_lower:
                            data['Giới tính'] = 'Nam'
        
                    # --- BƯỚC 4.5: TRÍCH XUẤT NGÀY CẤP ---
                    # Chỉ quét tìm Ngày cấp khi có từ khóa.
                    # Phải lọc bỏ 'sinh', 'hết hạn' để tránh bắt nhầm Ngày sinh (ở thẻ mới) hoặc Ngày hết hạn (ở thẻ cũ)
                    if ("ngày, tháng, năm" in line_lower or "date, month, year" in line_lower or "date of issue" in line_lower or "cấp" in line_lower) and "sinh" not in line_lower and "hết hạn" not in line_lower and "expiry" not in line_lower and "birth" not in line_lower:
                        for j in range(i, min(i+3, len(lines))):
                            m = re.search(r'\b\d{2}/\d{2}/\d{4}\b', lines[j])
                            if m:
                                data['Ngày cấp CCCD'] = m.group(0)
                                break
                
                # ---------------------------------------------------------
                # 5. FALLBACK CHO NGÀY SINH (Nếu thuật toán từ khóa thất bại)
                # Lấy mốc thời gian < 2020 để làm ngày sinh dự phòng
                # ---------------------------------------------------------
                if not data['Ngày sinh'] and all_dates:
                    first_date = all_dates[0]
                    try:
                        if int(first_date.split('/')[-1]) < 2020:
                            data['Ngày sinh'] = first_date
                    except: pass

                return data

def extract_ocr_data(image_path_or_cv2img):
    """
    Hàm xử lý OCR (Trích xuất văn bản từ ảnh) bằng AI Deepdoc_VietOCR.
    Hỗ trợ tự động xoay ảnh (rotation fallback) nếu không tìm thấy CCCD.
    """
    try:
        if isinstance(image_path_or_cv2img, str):
            import cv2
            img_to_ocr = cv2.imread(image_path_or_cv2img)
            if img_to_ocr is None:
                return {"CCCD": "", "CMND": "", "Họ tên": "", "Ngày sinh": "", "Giới tính": "", "Nơi thường trú gốc": "", "Ngày cấp CCCD": "", "OCR Side": ""}, "Không thể đọc file ảnh"
        else:
            img_to_ocr = image_path_or_cv2img
            
    except Exception as e:
        return {}, f"Lỗi thư viện OCR: {str(e)}", None
        
    try:
        import cv2
        import numpy as np
        
        # --- PASS 1: TÌM CHIỀU ẢNH TỐT NHẤT ---
        best_img = img_to_ocr
        best_data = {'CCCD': '', 'Họ tên': '', 'Ngày sinh': '', 'OCR Side': ''}
        best_note = "Ảnh mờ hoặc không thể nhận diện được"
        rotated_return = None
        
        text, is_vertical = extract_text_from_image(img_to_ocr, return_orientation=True)
        data = parse_ocr_text(text)
        
        if data['CCCD'] or (not data['CCCD'] and data['OCR Side'] == 'Front' and data['Họ tên']):
            best_data = data
            if is_vertical:
                best_img = cv2.rotate(img_to_ocr, cv2.ROTATE_90_COUNTERCLOCKWISE)
                rotated_return = best_img
                # Cập nhật lại data cho ảnh đã xoay để chính xác hơn (đôi khi xoay lại đọc tốt hơn)
                text_rot, _ = extract_text_from_image(best_img, return_orientation=True)
                data_rot = parse_ocr_text(text_rot)
                for k, v in data_rot.items():
                    if v and not best_data.get(k): best_data[k] = v
                best_note = "Lấy bằng OCR (Đã tự xoay chữ dọc)"
            else:
                best_note = "Lấy bằng OCR"
        else:
            # Fallback xoay để tìm chiều đúng
            rotations = [
                (cv2.ROTATE_90_COUNTERCLOCKWISE, "Xoay trái 90 độ"),
                (cv2.ROTATE_90_CLOCKWISE, "Xoay phải 90 độ"),
                (cv2.ROTATE_180, "Xoay 180 độ")
            ]
            for rot_code, rot_name in rotations:
                rotated = cv2.rotate(img_to_ocr, rot_code)
                # extract_text_from_image có thể nhận 1 biến trả về nếu không yêu cầu orientation
                # Ở đây code cũ dùng extract_text_from_image(rotated) mà không có return_orientation=False
                # Hàm mặc định return_orientation=False, trả về mỗi text.
                text_rot = extract_text_from_image(rotated)
                data_rot = parse_ocr_text(text_rot)
                if data_rot['CCCD'] or (data_rot['OCR Side'] == 'Front' and data_rot['Họ tên']):
                    best_data = data_rot
                    best_img = rotated
                    rotated_return = rotated
                    best_note = f"Lấy bằng OCR ({rot_name})"
                    break
            else:
                # Nếu xoay 4 hướng vẫn không được, giữ lại data gốc tốt nhất (nếu có)
                best_data = data
                best_note = "Lấy bằng OCR"

        # --- KIỂM TRA ĐIỀU KIỆN RETRY ---
        def missing_critical(d):
            if d.get('OCR Side') == 'Back':
                return not d.get('CCCD') or not d.get('Ngày cấp CCCD')
            return not d.get('CCCD') or not d.get('Họ tên') or not d.get('Ngày sinh')
            
        if missing_critical(best_data):
            # --- PASS 2: BỘ LỌC TƯƠNG PHẢN (CLAHE) ---
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            lab = cv2.cvtColor(best_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l2 = clahe.apply(l)
            lab = cv2.merge((l2,a,b))
            img_contrast = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            text_p2 = extract_text_from_image(img_contrast)
            data_p2 = parse_ocr_text(text_p2)
            
            merged = False
            for k, v in data_p2.items():
                if v and not best_data.get(k):
                    best_data[k] = v
                    merged = True
                    
            if merged:
                best_note += " + Lọc Tương phản"
                
            if missing_critical(best_data):
                # --- PASS 3: BỘ LỌC LÀM NÉT (SHARPENING) ---
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                img_sharpen = cv2.filter2D(best_img, -1, kernel)
                
                text_p3 = extract_text_from_image(img_sharpen)
                data_p3 = parse_ocr_text(text_p3)
                
                merged_p3 = False
                for k, v in data_p3.items():
                    if v and not best_data.get(k):
                        best_data[k] = v
                        merged_p3 = True
                
                if merged_p3:
                    best_note += " + Làm nét"

        # Nếu cả 3 pass vẫn trống toàn bộ
        if not best_data['CCCD'] and not best_data['Họ tên'] and not best_data['Ngày sinh']:
            return best_data, "Ảnh mờ hoặc không thể nhận diện được", rotated_return
            
        return best_data, best_note, rotated_return
    except Exception as e:
        return {}, f"Lỗi OCR: {str(e)}", None

def process_qr_string(qr_string):
    parts = qr_string.split('|')
    import re
    addr_raw = parts[5] if len(parts) > 5 else ''
    addr_clean = re.sub(r',\s*,', ',', addr_raw) # Thay thế ', ,' hoặc ',,' bằng ','
    addr_clean = re.sub(r'\s+', ' ', addr_clean).strip(', ')

    data = {
        'CCCD': parts[0] if len(parts) > 0 else '',
        'CMND': parts[1] if len(parts) > 1 else '',
        'Họ tên': parts[2] if len(parts) > 2 else '',
        'Ngày sinh': format_date(parts[3]) if len(parts) > 3 else '',
        'Giới tính': parts[4] if len(parts) > 4 else '',
        'Nơi thường trú gốc': addr_clean,
        'Ngày cấp CCCD': format_date(parts[6]) if len(parts) > 6 else '',
    }
    
    notes = []
    if not data['Ngày cấp CCCD']:
        notes.append('Thiếu ngày cấp')
    if not data['Nơi thường trú gốc']:
        notes.append('Thiếu nơi thường trú')
        
    return data, notes

def fetch_single_address(addr):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) Gecko/20100101 Firefox/151.0',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'x-kas': '89232422',
        'Origin': 'https://tienich.vnhub.com',
        'Referer': 'https://tienich.vnhub.com/'
    }
    try:
        import json, time
        payload = json.dumps({"address": addr})
        
        for attempt in range(3):
            try:
                response = requests.post(
                    'https://tienich.vnhub.com/api/wards', 
                    data=payload,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                res_data = response.json()
                
                if res_data.get('success') and res_data.get('data') and len(res_data['data']) > 0 and res_data['data'][0].get('address'):
                    return {
                        "original": addr,
                        "success": True,
                        "converted": res_data['data'][0]['address']
                    }
            except requests.exceptions.HTTPError as e:
                # Nếu là lỗi 500, 502, 503, 504 thì retry, còn 4xx thì thôi (vì lỗi do data)
                if response.status_code >= 500:
                    time.sleep(1.5 * (attempt + 1)) # Backoff delay: 1.5s, 3s, 4.5s
                    continue
                else:
                    break
            except requests.exceptions.RequestException:
                # Lỗi kết nối, timeout -> retry
                time.sleep(1.5 * (attempt + 1))
                continue
                
            # Nếu chạy đến đây mà API không lỗi nhưng success=false thì cũng chờ và thử lại
            time.sleep(1)
            
        return {
            "original": addr,
            "success": False,
            "error": "Không tìm thấy địa chỉ tương ứng"
        }
    except Exception as e:
        return {
            "original": addr,
            "success": False,
            "error": f"Lỗi API: {str(e)}"
        }

def call_address_api(address_list, max_workers=4):
    if not address_list:
        return []
        
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_address, addr): addr for addr in address_list}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            
    return results

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm

console = Console(record=True)

def run_wizard(input_dir):
    # Xóa dấu nháy đơn/kép nếu người dùng kéo thả thư mục vào terminal có sinh ra
    input_dir = input_dir.strip('\'"')

    if not input_dir or not os.path.isdir(input_dir):
        console.print(f"\n[bold red]❌ Lỗi:[/bold red] Thư mục '{input_dir}' không tồn tại hoặc đường dẫn không đúng.")
        Prompt.ask("[dim]Nhấn Enter để thử lại...[/dim]")
        return

    # Search for common image formats
    image_paths = []
    for ext in ('*.jpg', '*.jpeg', '*.png', '*.heic', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.HEIC', '*.WEBP'):
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

    if not image_paths:
        console.print("\n[bold red]❌ Thật tiếc, không tìm thấy file ảnh nào (.jpg, .png) trong thư mục này.[/bold red]")
        Prompt.ask("[dim]Nhấn Enter để thử lại...[/dim]")
        return

    console.print(f"\n[bold green]✅ Đã quét thư mục và tìm thấy tổng cộng {len(image_paths)} file ảnh.[/bold green]")
    
    # --- AUTO BACKUP AND RENAME LOGIC ---
    import zipfile
    import uuid
    zip_path = os.path.join(input_dir, "original.zip")
    
    if not os.path.exists(zip_path):
        console.print("[cyan]📦 Đang sao lưu các file ảnh gốc vào original.zip...[/cyan]")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in image_paths:
                    zipf.write(file_path, os.path.basename(file_path))
            
            console.print("[cyan]🔄 Đang đổi tên các file ảnh theo số thứ tự...[/cyan]")
            # Bước 1: Đổi tên thành tên tạm (để tránh ghi đè ngẫu nhiên)
            temp_paths = []
            for file_path in image_paths:
                ext = os.path.splitext(file_path)[1]
                temp_name = f"temp_{uuid.uuid4().hex[:8]}{ext}"
                temp_path = os.path.join(input_dir, temp_name)
                os.rename(file_path, temp_path)
                temp_paths.append((temp_path, ext))
                
            # Bước 2: Đổi tên thành số thứ tự
            new_image_paths = []
            for i, (temp_path, ext) in enumerate(temp_paths, 1):
                new_name = f"{i}{ext}"
                new_path = os.path.join(input_dir, new_name)
                os.rename(temp_path, new_path)
                new_image_paths.append(new_path)
                
            image_paths = new_image_paths
            console.print("[bold green]✅ Đã sao lưu và đổi tên thành công![/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Lỗi trong quá trình sao lưu/đổi tên: {e}[/bold red]")
            return
    else:
        console.print("[yellow]⚠️ Bỏ qua bước sao lưu và đổi tên do file original.zip đã tồn tại trong thư mục này.[/yellow]")
    # ------------------------------------
    
    # Cấu hình luồng xử lý
    num_threads_input = Prompt.ask("\n[cyan]Nhập số luồng xử lý ảnh song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
    try:
        num_threads = int(num_threads_input) if num_threads_input else 4
    except ValueError:
        console.print("[yellow]⚠️ Giá trị không hợp lệ, sử dụng mặc định: 4 luồng.[/yellow]")
        num_threads = 4

    api_threads_input = Prompt.ask("[cyan]Nhập số luồng gọi API địa chỉ song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
    try:
        api_threads = int(api_threads_input) if api_threads_input else 4
    except ValueError:
        console.print("[yellow]Số luồng không hợp lệ, dùng mặc định 4[/yellow]")
        api_threads = 4

    # Wizard confirmation
    confirm = Confirm.ask("\n[bold yellow]Bạn có muốn bắt đầu xử lý ngay bây giờ không?[/bold yellow]")
    if not confirm:
        console.print("[yellow]Đã hủy quá trình.[/yellow]")
        return

    console.print("\n")
    console.print(Panel(f"[bold cyan]🚀 BẮT ĐẦU XỬ LÝ {len(image_paths)} ẢNH VỚI {num_threads} LUỒNG...[/bold cyan]", border_style="green"))

    import tempfile
    import uuid
    temp_rotated_dir = os.path.join(tempfile.gettempdir(), f"cccd_exports_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_rotated_dir, exist_ok=True)

    processed_data = []
    seen_cccds = set()
    
    def process_single_image(img_path):
        qr_string, engine, err, img, qr_rotated_img = extract_qr_data(img_path)
        
        log_msgs = []
        if qr_string:
            log_msgs.append(f"[green]✅ [Đã quét mã QR bằng {engine}]:[/green] {qr_string}")
            
        row_data = {
            'Họ tên': '', 'CCCD': '', 'CMND': '', 'Giới tính': '',
            'Ngày sinh': '', 'Nơi thường trú gốc': '', 'Địa chỉ chuẩn hóa mới': '',
            'Ngày cấp CCCD': '', 'Nơi cấp': '', 'Ngày hết hạn': '', 'Phân loại': '', 'Ghi chú': '', 'QR Raw': '',
            'Image Path': os.path.basename(img_path),
            'Full Image Path': img_path,
            'Scan Type': 'error'
        }
        
        if qr_rotated_img is not None:
            # Lưu lại ảnh QR đã xoay chuẩn vào thư mục tạm
            temp_path = os.path.join(temp_rotated_dir, os.path.basename(img_path))
            cv2.imwrite(temp_path, qr_rotated_img)
            row_data['Full Image Path'] = temp_path
            img = qr_rotated_img # Cập nhật img để nếu fallback sang OCR thì OCR lấy luôn ảnh đã xoay
        notes = []

        if qr_string:
            row_data['Scan Type'] = 'QR_scanned'
            row_data['QR Raw'] = qr_string
            extracted, validation_notes = process_qr_string(qr_string)
            row_data.update(extracted)
            notes.extend(validation_notes)
        else:
            if err:
                notes.append(err)
            
            # Fallback to OCR
            if img is not None:
                log_msgs.append(f"[yellow]⚠️ Không đọc được QR, đang thử quét OCR...[/yellow]")
                ocr_data, ocr_note, rotated_img = extract_ocr_data(img)
                
                if rotated_img is not None:
                    # Lưu lại ảnh đã xoay chuẩn vào thư mục tạm thay vì ghi đè file gốc
                    temp_path = os.path.join(temp_rotated_dir, os.path.basename(img_path))
                    cv2.imwrite(temp_path, rotated_img)
                    row_data['Full Image Path'] = temp_path
                
                # In thông tin OCR ra màn hình
                parts = []
                if ocr_data.get('OCR Side'): parts.append(f"[{ocr_data['OCR Side']}]")
                if ocr_data.get('CCCD'): parts.append(f"CCCD: {ocr_data['CCCD']}")
                if ocr_data.get('Họ tên'): parts.append(f"Tên: {ocr_data['Họ tên']}")
                if ocr_data.get('Ngày sinh'): parts.append(f"NS: {ocr_data['Ngày sinh']}")
                if ocr_data.get('Ngày cấp CCCD'): parts.append(f"Ngày cấp: {ocr_data['Ngày cấp CCCD']}")
                
                ocr_print_info = ", ".join(parts) if parts else "Không nhận diện được chữ"
                log_msgs.append(f"[blue]ℹ️ Kết quả OCR:[/blue] {ocr_print_info}")
                
                if ocr_data.get('CCCD'):
                    row_data['Scan Type'] = 'OCR_scanned'
                row_data.update(ocr_data)
                notes.append(ocr_note)
                
        row_data['Nơi cấp'] = get_place_of_issue(row_data.get('QR Raw', ''))
        row_data['Ngày hết hạn'] = calculate_expiry_date(row_data.get('Ngày sinh', ''))
        row_data['Phân loại'] = get_card_type(row_data.get('QR Raw', ''))
        row_data['Ghi chú'] = '; '.join(notes)
        return row_data, log_msgs

    import re
    # Grouping and Merging Logic
    records = {} # mapping CCCD -> record
    
    # Process images in parallel and collect all returned raw data
    extracted_items = []
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    
    with progress:
        task_id = progress.add_task("[cyan]Đang quét ảnh...", total=len(image_paths))
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_img = {executor.submit(process_single_image, path): path for path in image_paths}
            for future in concurrent.futures.as_completed(future_to_img):
                img_path = future_to_img[future]
                try:
                    row_data, log_msgs = future.result()
                    extracted_items.append(row_data)
                    
                    # Print logs for this image above the progress bar
                    progress.console.print(f"[bold][{os.path.basename(img_path)}][/bold]")
                    for msg in log_msgs:
                        progress.console.print(f"  {msg}")
                except Exception as exc:
                    progress.console.print(f"[bold red]❌ Lỗi khi xử lý ảnh {os.path.basename(img_path)}:[/bold red] {exc}")
                finally:
                    progress.advance(task_id)
                
    console.print(Panel(f"[bold cyan]🔄 BẮT ĐẦU GỘP DỮ LIỆU...[/bold cyan]", border_style="green"))
    for item in extracted_items:
        cccd = item.get('CCCD')
        if not cccd: continue
        
        is_new_record = False
        if cccd not in records:
            records[cccd] = {
                'index': len(records) + 1,
                'Họ tên': '', 'CCCD': cccd, 'CMND': '', 'Giới tính': '',
                'Ngày sinh': '', 'Nơi thường trú gốc': '', 'Địa chỉ chuẩn hóa mới': '',
                'Ngày cấp CCCD': '', 'Nơi cấp': '', 'Ngày hết hạn': '', 'Phân loại': '', 'Ghi chú': [], 'QR Raw': '',
                'Ảnh mặt trước CCCD/CC': '',
                'Ảnh mặt sau CCCD/CC': '',
                'Đổi tên Ảnh mặt trước CCCD/CC': '',
                'Đổi tên Ảnh mặt sau CCCD/CC': '',
                'Full Image Path Front': '',
                'Full Image Path Back': '',
                'OCR Image Path Front': '',
                'Full OCR Image Path Front': '',
                'OCR Image Path Back': '',
                'Full OCR Image Path Back': '',
                'OCR Image Path Unknown': '',
                'Full OCR Image Path Unknown': '',
                'has_qr_data': False,
                'has_ocr_data': False
            }
            is_new_record = True
        
        record = records[cccd]
        person_idx = record['index']
        
        is_qr = bool(item.get('QR Raw'))
        if is_qr:
            id_type = 'CCCD' if len(str(cccd)) == 12 else 'CMND'
            if not is_new_record:
                if record['has_ocr_data'] and not record['has_qr_data']:
                    console.print(f"   [yellow]→ [Người {person_idx}] [GỘP DỮ LIỆU][/yellow] GHI ĐÈ thông tin từ ảnh {item['Image Path']} (Đọc mã QR) lên thông tin OCR trước đó của {id_type} {cccd}")
                elif record['has_qr_data']:
                    console.print(f"   [yellow]→ [Người {person_idx}] [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin từ ảnh {item['Image Path']} vì đã quét mã QR thành công trước đó cho {id_type} {cccd}")
            
            record['has_qr_data'] = True
            # Overwrite text fields with QR accuracy
            for k in ['Họ tên', 'CMND', 'Giới tính', 'Ngày sinh', 'Nơi thường trú gốc', 'Ngày cấp CCCD', 'Nơi cấp', 'Ngày hết hạn', 'Phân loại', 'QR Raw']:
                if item.get(k): record[k] = item[k]
            
            # Determine card type and side
            fields = item['QR Raw'].split('|')
            if len(fields) == 7:
                record['Ảnh mặt trước CCCD/CC'] = item['Image Path']
                record['Full Image Path Front'] = item['Full Image Path']
            elif len(fields) >= 10:
                record['Ảnh mặt sau CCCD/CC'] = item['Image Path']
                record['Full Image Path Back'] = item['Full Image Path']
            
            if item.get('Ghi chú'):
                record['Ghi chú'].append(item['Ghi chú'])
        else: # OCR
            id_type = 'CCCD' if len(str(cccd)) == 12 else 'CMND'
            if not is_new_record:
                if record['has_qr_data']:
                    console.print(f"   [yellow]→ [Người {person_idx}] [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin trùng lặp từ ảnh {item['Image Path']} (OCR) vì đã có dữ liệu QR chuẩn xác của {id_type} {cccd}")
                elif record['has_ocr_data']:
                    console.print(f"   [yellow]→ [Người {person_idx}] [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin trùng lặp từ ảnh {item['Image Path']} (OCR) vì đã xử lý ảnh OCR trước đó cho {id_type} {cccd}")
            
            record['has_ocr_data'] = True
            
            # Fill empty text fields
            for k in ['Họ tên', 'CMND', 'Giới tính', 'Ngày sinh', 'Nơi thường trú gốc', 'Ngày cấp CCCD']:
                if item.get(k) and not record.get(k): record[k] = item[k]
                
            if item.get('OCR Side') == 'Front':
                record['OCR Image Path Front'] = item['Image Path']
                record['Full OCR Image Path Front'] = item['Full Image Path']
            elif item.get('OCR Side') == 'Back':
                record['OCR Image Path Back'] = item['Image Path']
                record['Full OCR Image Path Back'] = item['Full Image Path']
            else:
                record['OCR Image Path Unknown'] = item['Image Path']
                record['Full OCR Image Path Unknown'] = item['Full Image Path']
            
            if item.get('Ghi chú'):
                record['Ghi chú'].append(item['Ghi chú'])

    # Pass 3: Assign OCR images to empty slots and Rename logic
    for cccd, record in records.items():
        # Assign Front
        if not record['Ảnh mặt trước CCCD/CC']:
            if record.get('OCR Image Path Front'):
                record['Ảnh mặt trước CCCD/CC'] = record.pop('OCR Image Path Front')
                record['Full Image Path Front'] = record.pop('Full OCR Image Path Front')
            elif record.get('OCR Image Path Unknown') and record['Ảnh mặt sau CCCD/CC']:
                record['Ảnh mặt trước CCCD/CC'] = record['OCR Image Path Unknown']
                record['Full Image Path Front'] = record['Full OCR Image Path Unknown']
                record['OCR Image Path Unknown'] = ''
                
        # Assign Back
        if not record['Ảnh mặt sau CCCD/CC']:
            if record.get('OCR Image Path Back'):
                record['Ảnh mặt sau CCCD/CC'] = record.pop('OCR Image Path Back')
                record['Full Image Path Back'] = record.pop('Full OCR Image Path Back')
            elif record.get('OCR Image Path Unknown') and record['Ảnh mặt trước CCCD/CC']:
                record['Ảnh mặt sau CCCD/CC'] = record['OCR Image Path Unknown']
                record['Full Image Path Back'] = record['Full OCR Image Path Unknown']
                record['OCR Image Path Unknown'] = ''

        if not record['Ảnh mặt trước CCCD/CC'] and not record['Ảnh mặt sau CCCD/CC']:
            if record.get('OCR Image Path Unknown'):
                record['Ghi chú'].append('Không thể phân biệt được ảnh này là mặt trước hay mặt sau do mờ và không chứa mã QR')

        hoten = record['Họ tên'] or 'KhongTen'
        cmnd = record['CMND']
        hoten_clean = hoten # keep space as user requested: Nguyễn Văn A_012_Mặt trước.jpg
        # Only remove illegal characters for filename
        hoten_clean = re.sub(r'[\\/*?:"<>|]', '', hoten_clean)
        cmnd_str = f"_{cmnd}" if cmnd else ""
        
        if record['Ảnh mặt trước CCCD/CC']:
            ext = os.path.splitext(record['Ảnh mặt trước CCCD/CC'])[1]
            record['Đổi tên Ảnh mặt trước CCCD/CC'] = f"{hoten_clean}_{cccd}{cmnd_str}_Mặt trước{ext}"
            
        if record['Ảnh mặt sau CCCD/CC']:
            ext = os.path.splitext(record['Ảnh mặt sau CCCD/CC'])[1]
            record['Đổi tên Ảnh mặt sau CCCD/CC'] = f"{hoten_clean}_{cccd}{cmnd_str}_Mặt sau{ext}"

    processed_data = list(records.values())
    # Lấy danh sách địa chỉ duy nhất
    unique_addresses = list(set([item['Nơi thường trú gốc'] for item in processed_data if item.get('Nơi thường trú gốc')]))
    console.print(Panel(f"[bold cyan]🌐 ĐANG CHUẨN BỊ GỌI API CHUẨN HÓA CHO {len(unique_addresses)} ĐỊA CHỈ DUY NHẤT VỚI {api_threads} LUỒNG...[/bold cyan]", border_style="green"))
    address_map = {}

    # Gọi API chuẩn hóa địa chỉ theo batch
    if unique_addresses:
        batch_size = 100
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as api_progress:
            api_task = api_progress.add_task("[cyan]Đang gọi API VNHub...", total=len(unique_addresses))
            
            for i in range(0, len(unique_addresses), batch_size):
                batch = unique_addresses[i:i+batch_size]
                api_results = call_address_api(batch, max_workers=api_threads)
                
                for result in api_results:
                    if result and 'original' in result:
                        address_map[result['original']] = result
                        api_progress.advance(api_task)

    # Cập nhật kết quả API vào dữ liệu
    for row in processed_data:
        addr = row.get('Nơi thường trú gốc')
        if addr and addr in address_map:
            result = address_map[addr]
            new_notes = []
            if row['Ghi chú']:
                new_notes.extend(row['Ghi chú'] if isinstance(row['Ghi chú'], list) else [row['Ghi chú']])
            
            if result.get('success'):
                converted_addr = result.get('converted', '')
                row['Địa chỉ chuẩn hóa mới'] = converted_addr
                if converted_addr.lower().strip() == addr.lower().strip():
                    new_notes.append("Địa chỉ không đổi")
                if result.get('notSure'):
                    new_notes.append("Địa chỉ chuyển đổi chưa chắc chắn")
            else:
                err_msg = result.get('error', 'Lỗi không xác định khi chuẩn hóa')
                new_notes.append(err_msg)
            
            row['Ghi chú'] = '; '.join(new_notes)
            
    # Pass 4: Final formatting and cleanup
    for cccd, record in records.items():
        # Đảm bảo Ghi chú là list
        raw_notes = record['Ghi chú']
        if isinstance(raw_notes, str):
            raw_notes = raw_notes.split('; ')
        elif not isinstance(raw_notes, list):
            raw_notes = []
            
        # Clean up "QR không đọc được" và "Lấy bằng OCR" note if we actually have a QR code
        final_notes = [n for n in raw_notes if n]
        if record.get('QR Raw'):
            final_notes = [n for n in final_notes if 'QR không đọc được' not in n and 'Lấy bằng OCR' not in n]
            if 'Đọc mã QR' not in final_notes:
                final_notes.insert(0, 'Đọc mã QR')
        
        # Xử lý logic CMND (Yêu cầu mới)
        if not record['CMND']:
            if record.get('QR Raw'):
                record['CMND'] = 'Không có'
            else:
                record['CMND'] = 'Chưa xác định'

        # Tính toán ngày hết hạn dựa trên ngày sinh nếu bị khuyết (rất hay gặp ở luồng OCR)
        if not record['Ngày hết hạn'] and record.get('Ngày sinh'):
            record['Ngày hết hạn'] = calculate_expiry_date(record['Ngày sinh'])
            record['Phân loại'] = 'Căn cước / CCCD'
                
        # Deduplicate notes and convert to string
        unique_notes = []
        for note in final_notes:
            # handle cases where notes were joined by '; '
            for subnote in note.split('; '):
                if subnote and subnote not in unique_notes:
                    unique_notes.append(subnote)
        record['Ghi chú'] = '; '.join(unique_notes)
            
    # Fix note formatting for those not processed by API
    for row in processed_data:
        if isinstance(row['Ghi chú'], list):
            row['Ghi chú'] = '; '.join(row['Ghi chú'])

    # Export to Excel
    print("Đang xuất file Excel...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    headers = [
        "STT", "Họ tên", "CCCD", "CMND", "Giới tính", "Ngày sinh", 
        "Nơi thường trú gốc", "Địa chỉ chuẩn hóa mới", "Ngày cấp CCCD", "Nơi cấp", "Ngày hết hạn", "Phân loại", "Ghi chú", "QR Raw", 
        "Ảnh mặt trước CCCD/CC", "Ảnh mặt sau CCCD/CC", "Đổi tên Ảnh mặt trước CCCD/CC", "Đổi tên Ảnh mặt sau CCCD/CC"
    ]
    
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for idx, row_data in enumerate(processed_data):
        row = [
            idx + 1,
            row_data['Họ tên'],
            row_data['CCCD'],
            row_data['CMND'],
            row_data['Giới tính'],
            row_data['Ngày sinh'],
            row_data['Nơi thường trú gốc'],
            row_data['Địa chỉ chuẩn hóa mới'],
            row_data['Ngày cấp CCCD'],
            row_data['Nơi cấp'],
            row_data['Ngày hết hạn'],
            row_data['Phân loại'],
            row_data['Ghi chú'],
            row_data.get('QR Raw', ''),
            row_data.get('Ảnh mặt trước CCCD/CC', ''),
            row_data.get('Ảnh mặt sau CCCD/CC', ''),
            row_data.get('Đổi tên Ảnh mặt trước CCCD/CC', ''),
            row_data.get('Đổi tên Ảnh mặt sau CCCD/CC', '')
        ]
        ws.append(row)

    # Adjust column widths slightly
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = min(adjusted_width, 40) # Max width 40

    console.print("\n")
    console.print(Panel("[bold cyan]✨ CHUẨN BỊ XUẤT FILE EXCEL ✨[/bold cyan]", border_style="green"))
    
    console.print("\n[bold yellow]Chọn vị trí lưu thư mục export (chứa các file kết quả):[/bold yellow]")
    console.print("  [cyan]1[/cyan]. Lưu ở cùng cấp thư mục với thư mục đang xử lý (Ví dụ: Thu_muc_anh_exports)")
    console.print("  [cyan]2[/cyan]. Lưu mặc định ở thư mục export của dự án (mặc định)")
    console.print("  [cyan]3[/cyan]. Nhập địa chỉ thư mục mong muốn")
    
    export_option = Prompt.ask("[bold cyan]Nhập lựa chọn của bạn[/bold cyan]", choices=["1", "2", "3"], default="2")
    
    if export_option == "1":
        clean_input_dir = os.path.normpath(input_dir)
        exports_dir = clean_input_dir + "_exports"
    elif export_option == "3":
        custom_dir = Prompt.ask("[bold cyan]Nhập đường dẫn thư mục mong muốn lưu kết quả[/bold cyan]").strip().strip('\'"')
        if not custom_dir:
            console.print("[yellow]Đường dẫn rỗng, quay về mặc định.[/yellow]")
            exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        else:
            exports_dir = custom_dir
    else:
        exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

    try:
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi tạo thư mục {exports_dir}: {e}. Quay về mặc định.[/bold red]")
        exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)
            
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"ket_qua_{timestamp}.xlsx"
    
    custom_name = Prompt.ask(f"[bold cyan]Nhập tên file Excel muốn lưu[/bold cyan] (nhấn Enter để dùng tên mặc định [yellow]'{default_filename}'[/yellow])").strip()
    if not custom_name:
        output_filename = os.path.join(exports_dir, default_filename)
    else:
        if not custom_name.endswith('.xlsx'):
            custom_name += '.xlsx'
        output_filename = os.path.join(exports_dir, custom_name)

    # Khôi phục các sheet phụ theo yêu cầu
    ws_qr = wb.create_sheet(title="QR_scanned")
    ws_qr.append(["STT", "Tên file"])
    qr_idx = 1
    for item in extracted_items:
        if item.get('Scan Type') == 'QR_scanned':
            ws_qr.append([qr_idx, item['Image Path']])
            qr_idx += 1
            
    ws_ocr = wb.create_sheet(title="OCR_scanned")
    ws_ocr.append(["STT", "Tên file"])
    ocr_idx = 1
    for item in extracted_items:
        if item.get('Scan Type') == 'OCR_scanned':
            ws_ocr.append([ocr_idx, item['Image Path']])
            ocr_idx += 1
            
    # Xác định các file bị trùng lặp hoặc không được sử dụng
    used_images = set()
    used_images = set()
    cccd_to_front = {}
    cccd_to_back = {}
    for row in processed_data:
        cccd = row.get('CCCD') or row.get('CMND')
        if row.get('Full Image Path Front'): 
            used_images.add(row['Full Image Path Front'])
            if cccd: cccd_to_front[cccd] = row.get('Ảnh mặt trước CCCD/CC', '')
        if row.get('Full Image Path Back'): 
            used_images.add(row['Full Image Path Back'])
            if cccd: cccd_to_back[cccd] = row.get('Ảnh mặt sau CCCD/CC', '')
        
    duplicate_files = []
    for item in extracted_items:
        if item['Full Image Path'] not in used_images:
            cccd = item.get('CCCD') or item.get('CMND')
            dup_with = ""
            if cccd:
                is_front = False
                is_back = False
                if item.get('QR Raw'):
                    fields = item['QR Raw'].split('|')
                    if len(fields) == 7: is_front = True
                    elif len(fields) >= 10: is_back = True
                elif item.get('OCR Side') == 'Front': is_front = True
                elif item.get('OCR Side') == 'Back': is_back = True
                
                if is_front and cccd in cccd_to_front:
                    dup_with = cccd_to_front[cccd]
                elif is_back and cccd in cccd_to_back:
                    dup_with = cccd_to_back[cccd]
                else:
                    dup_with = cccd_to_front.get(cccd) or cccd_to_back.get(cccd) or ""
            item['Duplicate With'] = dup_with
            duplicate_files.append(item)

    ws_dup = wb.create_sheet(title="duplicate")
    ws_dup.append(["STT", "Tên file", "Trùng lặp với"])
    for i, item in enumerate(duplicate_files, 1):
        ws_dup.append([i, item['Image Path'], item.get('Duplicate With', '')])
    
    wb.save(output_filename)
    
    with console.status("[bold green]Đang tạo các file nén zip phân loại ảnh...", spinner="dots"):
        import shutil
        
        # 1. original.zip
        original_zip_path = os.path.join(exports_dir, 'original.zip')
        with zipfile.ZipFile(original_zip_path, 'w') as zf:
            for path in image_paths:
                if os.path.exists(path):
                    zf.write(path, os.path.basename(path))
        console.print(f" [green]✓[/green] Đã tạo [bold]original.zip[/bold] với {len(image_paths)} file.")
        
        # 2. rename.zip
        rename_zip_path = os.path.join(exports_dir, 'rename.zip')
        with zipfile.ZipFile(rename_zip_path, 'w') as zf:
            count_rename = 0
            for row in processed_data:
                folder = "CCCD" if row.get("Phân loại") == "Căn cước công dân" else "CC"
                
                front_path = row.get('Full Image Path Front')
                if front_path and os.path.exists(front_path) and row.get('Đổi tên Ảnh mặt trước CCCD/CC'):
                    zf.write(front_path, f"{folder}/{row['Đổi tên Ảnh mặt trước CCCD/CC']}")
                    count_rename += 1
                    
                back_path = row.get('Full Image Path Back')
                if back_path and os.path.exists(back_path) and row.get('Đổi tên Ảnh mặt sau CCCD/CC'):
                    zf.write(back_path, f"{folder}/{row['Đổi tên Ảnh mặt sau CCCD/CC']}")
                    count_rename += 1
                    
        console.print(f" [green]✓[/green] Đã tạo [bold]rename.zip[/bold] với {count_rename} file đã được đổi tên (trong CC và CCCD).")
        
        # 3. Khôi phục lại các file nén phân loại cũ
        def create_zip_helper(zip_name, file_paths):
            if not file_paths:
                return
            zip_path = os.path.join(exports_dir, zip_name)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for fpath in file_paths:
                    if os.path.exists(fpath):
                        zf.write(fpath, os.path.basename(fpath))
            console.print(f" [green]✓[/green] Đã tạo [bold]{zip_name}[/bold] với {len(file_paths)} file.")

    qr_files = [item['Full Image Path'] for item in extracted_items if item.get('Scan Type') == 'QR_scanned']
    ocr_files = [item['Full Image Path'] for item in extracted_items if item.get('Scan Type') == 'OCR_scanned']
    dup_files = [item['Full Image Path'] for item in duplicate_files]
    
    create_zip_helper('QR_scanned.zip', qr_files)
    create_zip_helper('OCR_scanned.zip', ocr_files)
    create_zip_helper('duplicate.zip', dup_files)
    
    console.print("\n" + "🎉"*15)
    console.print(f"[bold green]ĐÃ HOÀN TẤT THÀNH CÔNG![/bold green]")
    console.print(f"File kết quả được lưu tại: [yellow]{os.path.abspath(output_filename)}[/yellow]")
    
    # Xuất file log
    log_filename = os.path.join(exports_dir, f"log_{timestamp}.txt")
    console.save_text(log_filename)
    console.print(f"File log chi tiết được lưu tại: [yellow]{os.path.abspath(log_filename)}[/yellow]")
    console.print("🎉"*15 + "\n")

def main():
    console.print(Panel.fit("[bold green]🚀 PHẦN MỀM TRÍCH XUẤT MÃ QR TỪ ẢNH CCCD RA EXCEL[/bold green]", border_style="cyan", padding=(1, 5)))
    
    with console.status("[bold green]Đang khởi tạo model AI...", spinner="dots"):
        init_models()
        
    first_run = True

    while True:
        input_dir = ""
        if first_run and len(sys.argv) >= 2:
            input_dir = sys.argv[1]
            first_run = False
        else:
            console.print("\n[yellow][Hướng dẫn][/yellow]: Kéo thả thư mục chứa ảnh vào cửa sổ này, hoặc copy đường dẫn thư mục và dán vào đây.")
            input_dir = Prompt.ask("[bold cyan]Nhập đường dẫn thư mục chứa ảnh CCCD (hoặc gõ 'q' để thoát)[/bold cyan]").strip()
            first_run = False
            
        if input_dir.lower() in ('q', 'quit', 'exit'):
            console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
            break
            
        run_wizard(input_dir)
        
        if not Confirm.ask("\n[bold yellow]Bạn có muốn tiếp tục xử lý thư mục khác không?[/bold yellow]"):
            console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
            break

if __name__ == '__main__':
    main()
