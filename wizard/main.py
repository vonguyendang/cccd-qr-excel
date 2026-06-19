import os
import sys
import glob
import tempfile
import uuid
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
import unicodedata
import concurrent.futures
import zipfile
import threading
import warnings

# Tắt cảnh báo chia cho 0 của numpy bên trong thư viện VietOCR
warnings.filterwarnings("ignore", category=RuntimeWarning, message="invalid value encountered in divide")

DEBUG_MODE = '--debug' in sys.argv

# Danh sách 300 họ phổ biến tiếng Việt (không dấu, lowercase)
_VN_SURNAMES = {
    'a', 'an', 'au', 'ba', 'bach', 'ban', 'bang', 'banh', 'bao', 'be',
    'bien', 'bo', 'bui', 'ca', 'cai', 'cam', 'can', 'cao', 'cap', 'cat',
    'chao', 'chau', 'che', 'chi', 'chiem', 'chiu', 'chu', 'chuc', 'chung', 'chuong',
    'co', 'cong', 'cu', 'cung', 'cut', 'dai', 'dam', 'dan', 'dang', 'danh',
    'dao', 'dau', 'deo', 'diec', 'diem', 'dien', 'diep', 'dieu', 'dinh', 'do',
    'doan', 'doi', 'dong', 'du', 'duong', 'duy', 'gian', 'giang', 'giap', 'ha',
    'hac', 'han', 'hang', 'hau', 'ho', 'hoa', 'hoang', 'hong', 'hua', 'hung',
    'huong', 'huynh', 'ka', 'kha', 'khau', 'khieu', 'khong', 'khuat', 'khuc', 'khuong',
    'khuu', 'kien', 'kieu', 'kim', 'la', 'lac', 'lai', 'lam', 'lang', 'lanh',
    'lao', 'lau', 'le', 'leng', 'leu', 'lien', 'lieng', 'lieu', 'linh', 'lo',
    'loc', 'loi', 'long', 'lu', 'luan', 'luc', 'luong', 'luu', 'luyen', 'ly',
    'ma', 'mac', 'mach', 'mai', 'man', 'mang', 'manh', 'mau', 'me', 'mo',
    'mong', 'moong', 'mua', 'nay', 'ngac', 'ngan', 'nghiem', 'ngo', 'ngoc', 'ngon',
    'ngu', 'nguy', 'nguyen', 'nham', 'nhan', 'nhu', 'nie', 'ninh', 'nong', 'o',
    'on', 'ong', 'pham', 'phan', 'phi', 'pho', 'phong', 'phu', 'phung', 'phuong',
    'quach', 'quan', 'quang', 'que', 'quyen', 'ro', 'sa', 'sai', 'sam', 'san',
    'son', 'su', 'sung', 'ta', 'tac', 'tan', 'tang', 'tao', 'tat', 'thach',
    'thai', 'tham', 'than', 'thang', 'thanh', 'thao', 'thi', 'thieu', 'tho', 'thoi',
    'thuong', 'thuy', 'tien', 'tiet', 'tieu', 'to', 'toan', 'ton', 'tong', 'tonnu',
    'tonthat', 'tra', 'trac', 'tram', 'tran', 'trang', 'tri', 'trieu', 'trinh', 'trung',
    'truong', 'tu', 'tuong', 'ung', 'uong', 'va', 'van', 'vang', 'vi', 'vien',
    'vinh', 'vo', 'vong', 'vu', 'vuong', 'vuu', 'vy', 'xa', 'xong', 'y',
    'yen',
}

def _is_valid_name(s):
    """Tên hợp lệ: 2-5 từ, bắt đầu bằng họ VN phổ biến, không số."""
    if not s or re.search(r'\d', s):
        return False
    words = s.strip().split()
    if not (2 <= len(words) <= 5):
        return False
    # Chuẩn hóa họ: xóa dấu để so sánh
    first = unicodedata.normalize('NFD', words[0].lower())
    first_ascii = ''.join(c for c in first if unicodedata.category(c) != 'Mn')
    return first_ascii in _VN_SURNAMES

# Danh sách 63 tỉnh/thành phố VN (không dấu, lowercase)
_VN_PROVINCES = {
    'an giang', 'ba ria-vung tau','ba ria - vung tau','ba ria', 'vung tau', 'bac giang', 'bac kan', 'bac lieu', 'bac ninh', 'ben tre', 'binh dinh', 'binh duong', 'binh phuoc',
    'binh thuan', 'ca mau', 'can tho', 'cao bang', 'da nang', 'dak lak', 'dak nong', 'dien bien', 'dong nai', 'dong thap',
    'gia lai', 'ha giang', 'ha nam', 'ha noi', 'ha tinh', 'hai duong', 'hai phong', 'hau giang', 'hcm', 'ho chi minh',
    'hoa binh', 'hung yen', 'khanh hoa', 'kien giang', 'kon tum', 'lai chau', 'lam dong', 'lang son', 'lao cai', 'long an',
    'nam dinh', 'nghe an', 'ninh binh', 'ninh thuan', 'phu tho', 'phu yen', 'quang binh', 'quang nam', 'quang ngai', 'quang ninh',
    'quang tri', 'soc trang', 'son la', 'tay ninh', 'thai binh', 'thai nguyen', 'thanh hoa', 'thua thien hue', 'tien giang', 'tra vinh',
    'tuyen quang', 'vinh long', 'vinh phuc', 'vung tau', 'yen bai',
}

# Global locks
ocr_lock = threading.Lock()
qr_lock = threading.Lock()

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
        with qr_lock:
            qr_data, engine, center = _try_scan(img)
        
        # 2. Quét góc phần tư phía trên bên phải (CCCD) nếu toàn bộ ảnh thất bại
        if not qr_data:
            h, w = img.shape[:2]
            crop = img[0:int(h/2), int(w/2):w]
            with qr_lock:
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
                    'OCR Side': '', 'Raw Text Upper': text.upper() if text else '',
                    'Raw Text': text if text else ''
                }

                if not text.strip():
                    return data

                text_upper = text.upper()

                # ---------------------------------------------------------
                # 1. NHẬN DIỆN MẶT THẺ (FRONT / BACK)
                if "<<" in text_upper or "IDVNM" in text_upper or "ĐẶC ĐIỂM NHẬN DẠNG" in text_upper or "NGÓN TRỎ" in text_upper or "CỤC TRƯỞNG" in text_upper or "BỘ CÔNG AN" in text_upper:
                    data['OCR Side'] = 'Back'
                # Các từ khóa đặc trưng của Mặt Trước
                elif "CĂN CƯỚC" in text_upper or "CẦN CƯỚC" in text_upper or "CÔNG DÂN" in text_upper or "ĐỘC LẬP" in text_upper or "TỰ DO" in text_upper or "HỌ VÀ TÊN" in text_upper:
                    data['OCR Side'] = 'Front'

                # ---------------------------------------------------------
                # 2. TRÍCH XUẤT SỐ CCCD
                # ---------------------------------------------------------
                text_mrz = text_upper.replace('O', '0') 
                
                # Quy tắc vàng: 12 chữ số liên tiếp nằm ngay liền trước dấu '<'
                # Duyệt qua TẤT CẢ vị trí match, ưu tiên lấy cái bắt đầu bằng 0
                for mrz_m in re.finditer(r'(\d{12})<', text_mrz):
                    candidate = mrz_m.group(1)
                    if candidate.startswith('0'):
                        data['CCCD'] = candidate
                        data['OCR Side'] = 'Back'
                        break

                # Nếu không tìm thấy pattern <, thử lắp ráp từ VNM chuẩn ICAO
                if not data['CCCD']:
                    mrz_match = re.search(r'VNM(\d{9})\d(\d{3})', text_mrz)
                    if mrz_match:
                        assembled = mrz_match.group(2) + mrz_match.group(1)
                        if assembled.startswith('0') and len(assembled) == 12:
                            data['CCCD'] = assembled
                            data['OCR Side'] = 'Back'

                # Nếu vẫn chưa có: tìm dòng/khối IDVNM, gom ký tự số + '<' từ khối đó
                # Bỏ 3 ký tự cuối (<<X), lấy 12 ký tự cuối còn lại = CCCD
                # Lưu ý: OCR có thể vỡ dòng MRZ ra nhiều dòng nhỏ → gom cả khối 5 dòng tiếp theo
                # Lưu ý: MRZ không có chữ O → mọi 'O' đều là số 0 bị OCR đọc sai
                if not data['CCCD']:
                    mrz_lines = text_mrz.split('\n')  # text_mrz đã replace O→0 rồi
                    for i, line in enumerate(mrz_lines):
                        line_stripped = line.strip()
                        if line_stripped.startswith('IDVN'):
                            # Gom: dòng IDVNN + tối đa 5 dòng tiếp theo (MRZ có thể wrap)
                            block_lines = mrz_lines[i:i+6]
                            block = ' '.join(block_lines)
                            # Bỏ tiền tố IDVNM/IDVNN
                            after_prefix = re.sub(r'^IDVN[NM0]', '', block.strip())
                            # Chỉ giữ lại chữ số và dấu '<' (MRZ không có chữ O)
                            cleaned = re.sub(r'[^0-9<]', '', after_prefix)
                            # Cần ít nhất 15 ký tự: 3 cuối (<<X) + 12 CCCD
                            if len(cleaned) >= 15:
                                candidate = cleaned[:-3][-12:]  # bỏ 3 cuối, lấy 12 cuối
                                if len(candidate) == 12 and candidate.startswith('0'):
                                    data['CCCD'] = candidate
                                    data['OCR Side'] = 'Back'
                            break

                # ------- MẶT TRƯỚC (Front): không có MRZ, quét số trực tiếp -------
                # Chỉ chạy nếu chưa có CCCD từ MRZ VÀ thẻ không phải mặt sau
                # Tránh tình trạng mặt sau bị OCR rác ra ngẫu nhiên 12 chữ số
                if not data['CCCD'] and data['OCR Side'] != 'Back':
                    text_numbers = text_upper.replace('O', '0')
                    # Lấy tất cả cụm 12 số đứng độc lập bắt đầu bằng 0
                    # Dùng re.sub loại toàn bộ whitespace (kể cả \n \t) để tránh đếm sai độ dài
                    cccd_matches = re.findall(r'\b(0[\d\s]{11,15})\b', text_numbers)
                    valid_cccds = []
                    for match_str in cccd_matches:
                        val = re.sub(r'\s+', '', match_str)  # loại mọi whitespace kể cả \n
                        if len(val) == 12:
                            valid_cccds.append(val)
                    
                    if valid_cccds:
                        # Ưu tiên cụm nằm trên dòng có chứa từ khóa 'SỐ'/'CƯỚC' (nhãn số thẻ)
                        data['CCCD'] = valid_cccds[0]
                        data['OCR Side'] = 'Front'
                        for line in text_upper.split('\n'):
                            if 'SỐ' in line or 'CƯỚC' in line:
                                m = re.search(r'\b(0[\d\s]{11,15})\b', line.replace('O','0'))
                                if m:
                                    val = re.sub(r'\s+', '', m.group(1))
                                    if len(val) == 12:
                                        data['CCCD'] = val
                                        data['OCR Side'] = 'Front'
                                        break
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
        
                # ---------------------------------------------------------
                # 3b. TRÍCH XUẤT TÊN TỪ MRZ LINE 3 (BACK SIDE)
                # MRZ line 3 có format: SURNAME<<GIVEN<NAMES<<<
                # OCR đọc nhầm: '<' → 'C'/'K', '<<' → 'CK'/'CC', padding → 'ES'/'CECCES'...
                # Ví dụ: TRAN<LE<THAO<<NGUYEN<<< → TRANCKLECTHAOCNGUYENCECCES
                # ---------------------------------------------------------
                if data['OCR Side'] == 'Back' and not data['Họ tên']:
                    def _extract_mrz_name_words(s):
                        """Tách các từ tên thực sự từ chuỗi MRZ bằng thuật toán Greedy Match với từ điển."""
                        s = re.sub(r'[CKEA<S]{3,}$', '', s)
                        
                        # Sửa các lỗi OCR kinh điển làm biến dạng từ
                        ocr_fixes = {
                            "HHONGE": "HONG",
                            "CIEU": "KIEU",
                            "TRUECRE": "TRUC",
                            "TRUEC": "TRUC",
                            "EVINH": "VINH",
                            "STRAN": " TRAN",
                            "NGOCNUOI": "NGOC NUOI",
                            "HUYNE": "HUYNH",
                            "THUYKHANG": "THUY HANG",
                            "THUCTRANGCA": "THU TRANG",
                            "THUCTRANG": "THU TRANG",
                            "CHUYNH": "HUYNH"
                        }
                        for bad, good in ocr_fixes.items():
                            s = s.replace(bad, good)
                        
                        # Danh sách âm tiết tên Tiếng Việt phổ biến (không dấu)
                        common_names = "AN ANH BA BAC BAN BANG BAO BE BEN BICH BINH BO BON CA CAN CANH CAO CAT CHAU CHI CHIEN CHINH CHU CHUAN CHUNG CHUYEN CON CUC CUONG DA DAI DAN DANG DAO DAT DAU DE DIEN DIEP DIEU DINH DO DOAN DOANH DONG DU DUC DUNG DUONG DUY DUYEN EM GIA GIANG GIAO GIAP HA HAI HAN HANG HANH HAO HE HIEN HIEP HIEU HINH HOA HOAI HOAN HOANG HOI HONG HOP HUNG HUONG HUU HUY HUYEN HUYNH ICH KHA KHAI KHANG KHANH KHAO KHE KHOA KHOI KHUE KHUYEN KIEN KIEU KIM KY LA LAM LAN LANG LANH LAP LE LIEN LIEU LINH LOAN LOC LOI LONG LUA LUAN LUC LUONG LUU LY MAI MAN MANG MANH MAO MAU MINH MOC MONG MUOI MY NAM NGA NGAN NGANH NGHI NGHIA NGHIEM NGOC NGON NGU NGUYEN NGUYET NHA NHAN NHAT NHI NHIEN NHO NHU NHUAN NHUNG NIEN NINH NOAN NU NUOI NUONG OA OANH PHA PHAI PHAN PHANG PHAT PHI PHIEN PHONG PHU PHUC PHUC PHUNG PHUONG QUAN QUANG QUE QUOC QUY QUYEN QUYNH RAO SA SAM SAN SANG SAU SEN SINH SOA SON SONG SUONG SY TA TAI TAM TAN TANG TANH TAO TAY THA THACH THAI THAM THAN THANH THAO THAT THAY THE THI THIEN THIET THIEU THINH THOA THOAI THOM THU THUAN THUC THUONG THUY THUYEN THY TIEN TIEP TIN TINH TO TOA TOAN TOAI TONG TRA TRAM TRAN TRANG TRANH TRAO TRI TRIEU TRINH TRONG TRU TRUC TRUNG TRUYEN TU TUAN TUAT TUE TUI TUNG TUY TUYEN TUYET UYEN VAN VANG VY VI VIEN VIET VINH VO VONG VU VUONG VY XUA XUAN Y YEN"
                        names_list = sorted(list(set(common_names.split())), key=len, reverse=True)
                        pattern = r'(' + '|'.join(names_list) + r')'
                        
                        matches = re.findall(pattern, s)
                        return matches

                    for line in text_upper.split('\n'):
                        # OCR đôi khi sinh ra khoảng trắng giữa các chữ trong MRZ -> Xóa toàn bộ khoảng trắng
                        ls = line.replace(' ', '').strip()
                        
                        # Chặn các dòng tiếng Anh hoặc tiếng Việt không dấu bị nhận diện nhầm
                        if any(bad in ls for bad in ['IDEN', 'NATIO', 'SONAL', 'CANCUOC', 'CONGDAN', 'TRUONG', 'GIAMDOC', 'INDEX', 'FINGER', 'ADMIN', 'POLICE', 'DIRECTOR', 'ORDER']):
                            continue
                            
                        # MRZ Line 3 chứa tên, KHÔNG có số, KHÔNG có dấu tiếng Việt
                        # OCR đọc dấu << thành CK, CC, CE, KCK...
                        if (15 <= len(ls) <= 40
                            and re.match(r'^[A-Z<]+$', ls)  # Chỉ gồm chữ cái A-Z và < (không có số, không dấu)
                            and re.search(r'[<CKE]{2}', ls) # Chắc chắn có ít nhất 1 cụm 2 ký tự độn (CK, CC, CE...) thay cho <<
                            and not ls.startswith('IDVN')
                            and not ls.startswith('VNM')
                        ):
                            # Tách Họ và Đệm+Tên dựa trên 2 dấu << liên tiếp (OCR -> CC, CK, CE, CEC...)
                            split_parts = re.split(r'CK|CEC|KCK|CC|CE|CS|EK(?=[A-Z])', ls, maxsplit=1)
                            if len(split_parts) == 2:
                                surname_words = _extract_mrz_name_words(split_parts[0])
                                given_words   = _extract_mrz_name_words(split_parts[1])
                                words = surname_words + given_words
                            else:
                                words = _extract_mrz_name_words(split_parts[0])
                            if len(words) >= 2:
                                data['Họ tên'] = ' '.join(words)
                                break


                lines = [line.strip() for line in text.split('\n') if line.strip()]

                # ---------------------------------------------------------
                # 4. DUYỆT TỪNG DÒNG (VÉT THÔNG TIN: TÊN, ĐỊA CHỈ, NGÀY THÁNG)
                # OCR đọc ảnh từ trên xuống dưới, nên ta duyệt từng dòng để bắt từ khóa
                # ---------------------------------------------------------
                for i, line in enumerate(lines):
                    line_lower = line.lower()
    
                    # 1. Name
                    if any(kw in line_lower for kw in ["họ và tên", "họ chữ đệm và tên", "full name", "ho ten", "kho và tên", "fui nam"]):
                        if ":" in line:
                            name_part = line.split(":", 1)[1].strip()
                            name_part = name_part.rstrip('.')
                            # Cắt tại dấu phẩy đầu tiên để loại bỏ phần dính sau (VD: "Nguyen Thi Diem Truc, Ngay sinh:")
                            name_part = name_part.split(',')[0].strip()
                            if (name_part.isupper() or name_part.istitle()) and len(name_part) > 3 and _is_valid_name(name_part):
                                data['Họ tên'] = name_part
                        
                        # Nếu không có dấu 2 chấm, thử lấy dòng tiếp theo
                        if not data['Họ tên'] and i + 1 < len(lines):
                            next_line = lines[i+1].replace('|', '').strip()
                            # Phải viết hoa (ALLCAPS hoặc Title Case) VÀ bắt đầu bằng họ VN hợp lệ
                            if ((next_line.isupper() or next_line.istitle())
                                    and len(next_line) > 3
                                    and not re.search(r'\d', next_line)
                                    and _is_valid_name(next_line)
                                    and not any(kw in next_line.lower() for kw in ['ngày', 'sinh', 'quốc', 'tịch', 'giới', 'tính'])):
                                data['Họ tên'] = next_line
                
                    # 2. DOB
                    if "sinh" in line_lower or "birth" in line_lower:
                        for j in range(i, min(i+2, len(lines))):
                            m = re.search(r'\b\d{2}/\d{2}/\d{4}\b', lines[j])
                            if m:
                                data['Ngày sinh'] = m.group(0)
                                break
                
                    # --- BƯỚC 4.3: TRÍCH XUẤT ĐỊA CHỈ (NƠI THƯỜNG TRÚ/CƯ TRÚ) ---
                    if "nơi thường trú" in line_lower or "nơi cư trú" in line_lower or "residence" in line_lower or "thuong tru" in line_lower or "trương vú" in line_lower:
                        addr_parts = []
                        if ":" in line:
                            val = line.split(":", 1)[1].strip()
                        else:
                            m = re.split(r'(?i)(nơi thường trú|nơi cư trú|place of residence|residence|thuong tru|trương vú)[^a-z0-9]*', line)
                            val = m[-1].strip() if len(m) > 2 else ""
                            
                        # Loại bỏ các chuỗi nhiễu có thể bám ngay cùng dòng
                        val = re.sub(r'(?i)(giới tính|quốc tịch|sex|nationality|(có )?gi[aáà] trị đ[ếêề]n\s*[:.,]*|expiry|date).*', '', val).strip()
                        if len(val) >= 2:
                            addr_parts.append(val)
        
                        # Quét các dòng tiếp theo để nối đuôi địa chỉ do địa chỉ thường rất dài và bị rớt dòng.
                        for j in range(i + 1, min(i + 7, len(lines))):
                            next_line = lines[j].replace('|', '').strip()
                            next_lower = next_line.lower()
                            
                            current_addr = ", ".join(filter(bool, addr_parts))
                            commas_count = current_addr.count(',')
                            
                            # CÁC TỪ KHOÁ NGẮT (BREAK) - Rác ngoài thẻ hoặc Mặt sau
                            hard_stops = [
                                "zalo", "chữ ký", "qr", "từ mã", "đặc điểm nhận dạng",
                                "ngón trỏ trái", "ngón trỏ phải", "ngón trỏ",  # cụ thể hơn "trái"/"phải"
                                "vân tay trái", "vân tay phải"
                            ]
                            soft_stops = [
                                "ngày sinh", "date of birth", "ngày, tháng, năm", "date, month",
                                "ngày cấp", "date of issue", "date issue", "ddate", "ddate issue",
                                "nơi cấp", "place of issue", "place ofresic",
                                "ngày hết hạn", "expiry", "hết hạn", "ferpiry", "date ferpiry",
                                "giá trị đến", "có giá trị",
                                "gia tri đến", "gia tri đen",  # biến thể không dấu OCR
                                "giới tính", "quốc tịch",
                            ]
                            
                            if any(stop_word in next_lower for stop_word in hard_stops):
                                break
                            
                            if any(stop_word in next_lower for stop_word in soft_stops):
                                # Nếu địa chỉ chưa đủ dài (dưới 4 dấu phẩy, địa chỉ VN thường 2-5 dấu phẩy),
                                # có thể đang quét thẻ 2 cột (layout "giá trị đến" nằm song song với địa chỉ).
                                # Bỏ qua break để cho phép regex bên dưới xóa nhãn này và lấy phần địa chỉ còn lại.
                                if commas_count < 4:
                                    pass
                                else:
                                    break
                                
                            clean_line = next_line
                            # Xóa cụm "giá trị đến" và mọi biến thể OCR (có/không dấu)
                            # "gia tri đến", "giá trị đến", "gia tri den", v.v.
                            clean_line = re.sub(
                                r'(?i)(c[oó]\s+)?gi[aáà]\s*tr[iị]\s*(đ[ếeêề]n|den|đen)\s*[:.,]*',
                                '', clean_line).strip()
                            clean_line = re.sub(
                                r'(?i)(expiry|h[eế]t\s*h[aạ]n|ferpiry|date\s*ferpiry|date\s*ferp[a-z]*|'
                                r'n[oơ]i\s*c[aấ]p|ng[aà]y\s*c[aấ]p|b[oộ]\s*c[oô]ng\s*an|c[uụ]c\s*c[aả]nh\s*s[aá]t|'
                                r'gi[oớ]i\s*t[ií]nh|qu[oố]c\s*t[iị]ch|sex|nationality|'
                                r'qu[eê]\s*qu[aá]n|khai\s*sinh|birth|data\s*ofespry)',
                                '', clean_line).strip()
                            
                            # Xóa ngày tháng năm
                            clean_line = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', '', clean_line).strip()
                                
                            # CẮT BỎ CÁC TỪ TIẾNG ANH ẢO GIÁC DO OCR NHẬN DIỆN MỜ VÀ CÁC NHÃN
                            clean_line = re.sub(
                                r'(?i)\b(place\s*of\s*res[a-z]*|place\s*ofresic|i\s*place|pplace|ppace|place|'
                                r'date\s*of\s*issue|ddate|ddate\s*issue|dddate|ddate\s*issue|date\s*issue|issue|'
                                r'indent|vi[eê][nǹ]|nam\s+linh|'
                                r'place of residence|place of origin|place oforging|transervating|daleoroxic|'
                                r'deleofexpin|overstreeter|residence|origin|'
                                r'họ và tên 1 full name|số 1 noi|con minh gian|moroot|full name|họ và tên|'
                                r'sedest|ingave|1tho|nams|cang 10/000020|notter|cachoro|stard|fui nam|kho và tên|of|cccd)\b',
                                '', clean_line).strip()
                            clean_line = re.sub(r'(?i)(họ và tên 1 full name|số 1 noi|con minh gian|moroot|sedest|ingave|1tho|nams|cang 10/000020|notter|cachoro|stard|fui nam|kho và tên|of|cccd)', '', clean_line).strip()
                            
                            # Loại bỏ chữ 'Có' rớt lại do cắt cụm 'Có giá trị đến' bị thiếu
                            # Xử lý các dạng: 'Có :', 'Có', 'Có ,' đứng 1 mình hoặc kẹp ở đầu/cuối chuỗi
                            clean_line = re.sub(r'(?i)^(c[oó]|co\u0301)\s*[:.,]*\s*', '', clean_line).strip()
                            clean_line = re.sub(r'(?i)\s+(c[oó]|co\u0301)\s*[:.,]*$', '', clean_line).strip()
                            
                            # Cắt bỏ rác là số CCCD (12 số) hoặc số điện thoại lọt vào địa chỉ, và ngày tháng bị dính (vd 1010/2037)
                            clean_line = re.sub(r'\b\d{10,12}\b', '', clean_line).strip()
                            clean_line = re.sub(r'\b\d{4}/\d{4}\b', '', clean_line).strip()
                            
                            # Không lấy vào địa chỉ nếu dòng này lọt Họ Tên vào
                            if data.get('Họ tên') and clean_line == data['Họ tên']:
                                continue

                            if len(clean_line) >= 2:
                                # Chống lặp: chỉ skip nếu giống HỆT dòng đã có (case-insensitive)
                                # KHÔNG dùng substring check — sẽ bỏ sót dòng địa chỉ dài hơn
                                is_dup = any(
                                    clean_line.lower() == p.lower()
                                    for p in addr_parts
                                )
                                if not is_dup:
                                    addr_parts.append(clean_line)
                                    
                                    # Kiểm tra xem dòng vừa thêm có phải điểm cuối địa chỉ (chứa tên tỉnh thành) không
                                    # Chuẩn hóa về không dấu lowercase để so sánh
                                    cl_lower = clean_line.lower().replace("đ", "d").replace("-", " ")
                                    cl_nfd = unicodedata.normalize('NFD', cl_lower)
                                    cl_ascii = "".join(c for c in cl_nfd if unicodedata.category(c) != 'Mn')
                                    
                                    is_end = False
                                    for p in _VN_PROVINCES:
                                        # Tìm bằng regex word boundary để tránh match một phần (VD: 'an giang' trong chuỗi khác)
                                        import re
                                        matches = list(re.finditer(r'\b' + re.escape(p) + r'\b', cl_ascii))
                                        if matches:
                                            # Lấy match cuối cùng trên dòng
                                            last_match = matches[-1]
                                            prefix_str = cl_ascii[:last_match.start()].strip().strip(',')
                                            
                                            # Kiểm tra xem ngay trước tỉnh/thành có phải là tiền tố cấp quận/huyện/thành phố không
                                            # VD: "tp soc trang", "thanh pho ben tre", "tx", "thi xa"
                                            is_sub_admin = False
                                            for prefix in ['tp', 'thanh pho', 'tx', 'thi xa', 'huyen', 'quan']:
                                                if prefix_str.endswith(prefix):
                                                    is_sub_admin = True
                                                    break
                                            
                                            if not is_sub_admin:
                                                is_end = True
                                                break
                                                
                                    if is_end:
                                        break
                
                        addr = ", ".join(filter(bool, addr_parts))
                        
                        # Dọn rác cứng đầu có thể lọt vào cuối đuôi địa chỉ (như CCCD, Có, dấu phẩy thừa)
                        addr = re.sub(r'(?i)[,.\s]+(cccd|có|co\u0301|of)\s*[:.,]*\s*$', '', addr).strip()
                        addr = re.sub(r'(?i)\b(cccd)\b', '', addr).strip()
                        
                        # Xóa các từ viết tắt hành chính: X. P. Q. H. T. TP. TX. TT. (có hoặc không có dấu chấm)
                        addr = re.sub(r'(?i)\b(x|p|q|h|t|tp|tx|tt)[\.\s]+', '', addr)
                        
                        # Fix các lỗi typo kinh điển của VietOCR khi đọc thẻ mờ ở Cần Thơ và các tỉnh khác
                        typo_fixes = {
                            # --- Cần Thơ variants ---
                            "Ninh Kiơu Thơ": "Ninh Kiều, Cần Thơ",
                            "Ninh Kiơn Thơ": "Ninh Kiều, Cần Thơ",
                            "Ninh Kiểu": "Ninh Kiều",
                            "Ninh ciều": "Ninh Kiều",
                            "Cần Thơng": "Cần Thơ",
                            "Cần Thợ": "Cần Thơ",
                            "Cán Thơng Chinh": "Cần Thơ",
                            "Cán Thơng": "Cần Thơ",
                            "Thơng Chinh": "Cần Thơ",
                            "Thơng Chình": "Cần Thơ",
                            "Thơng Chính": "Cần Thơ",
                            "Thung Chinh": "Cần Thơ",
                            "Thung Chình": "Cần Thơ",
                            "Thung, Cán": "Cần Thơ",
                            "Thung": "Cần Thơ",
                            "Cán Thơ": "Cần Thơ",
                            "Cần Thơng Chinh": "Cần Thơ",
                            "Bình Thủy Thơ": "Bình Thủy, Cần Thơ",
                            "BẦN THỚ": "Bình Thủy, Cần Thơ",
                            "Bần Thớ": "Bình Thủy, Cần Thơ",
                            "CẦN THO": "CẦN THƠ",
                            # --- Số bị đọc nhầm ---
                            "Ấp Trà Canh AL": "Ấp Trà Canh A1",
                            " AL,": " A1,",  # Đề phòng trường hợp chung chung số 1 bị đọc thành L
                            "Đồng Nai Thu": "Đồng Nai",
                            # --- Dấu câu và ký hiệu lạ bị dính ---
                            "TP-Sóc Trăng": "TP. Sóc Trăng",
                            "TP-": "TP. ",
                        }
                        # Thêm khoảng trắng khi TP/TX/TT dính liền vào tên tỉnh/thành không có dấu phân cách
                        # VD: "TPCần Thơ" → "TP Cần Thơ", "TXTân An" → "TX Tân An"
                        addr = re.sub(r'\b(TP|TX|TT)([A-ZĐÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂẮẶẦẤƠỜƯỚƯỪ])',
                                      r'\1 \2', addr)
                        for wrong, right in typo_fixes.items():
                            addr = addr.replace(wrong, right)
                        
                        # Dùng regex để thay thế các từ đơn ngắn nguy hiểm hơn (tránh false-positive)
                        addr = re.sub(r'\bThung\b', 'Cần Thơ', addr)
                        
                        # Dùng regex để xóa các cụm "Cần Thơ" bị lặp lại liên tiếp (có thể cách nhau bằng khoảng trắng hoặc dấu phẩy)
                        addr = re.sub(r'(?:Cần Thơ[,\s]*){2,}', 'Cần Thơ', addr)
                        
                        # Regex loại bỏ các pattern lặp lại do OCR đọc cùng 1 đoạn nhiều lần
                        # Ví dụ: "Cần Thơ, Cần Thơ, Cần Thơ" → "Cần Thơ"
                        def _dedup_repeated_phrases(text):
                            """Xóa các cụm từ bị lặp lại liên tiếp (trường hợp OCR đọc nhiều lần)."""
                            # Tách theo dấu phẩy, loại trùng lặp liên tiếp
                            parts = [p.strip() for p in text.split(',') if p.strip()]
                            deduped = []
                            for p in parts:
                                if not deduped or p.lower() != deduped[-1].lower():
                                    deduped.append(p)
                            return ', '.join(deduped)
                        addr = _dedup_repeated_phrases(addr)
                        
                        # Xóa các nhãn tiếng Anh bị OCR hallucinate còn sót trong địa chỉ,
                        # và các cụm nhãn tiếng Việt còn sót ("Nơi đăng ký", "Ngày sinh I")
                        addr = re.sub(
                            r'(?i)\b(pplace|ppace|i\s*place|place\s*ofresic|ofresic|'
                            r'ddate|ddte|ddate\s*issue|date\s*issue|date\s*ferpiry|ferpiry|ferp[a-z]+|'
                            r'nam\s+linh|indent|'
                            r'disconning|nterting|interting|disconnected|'
                            r'issue|noi\s*dang\s*ky)\b',
                            '', addr).strip()
                        # Xóa cụm ALL-CAPS >= 6 ký tự không phải địa danh VN hợp lệ
                        # (rác OCR thường viết hoa toàn bộ, không có dấu tiếng Việt)
                        addr = re.sub(r'(?<![A-ZĐÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂẮẶẦẤƠỜƯỚƯỪ])'  # không đứng sau chữ hoa VN
                                      r'\b[A-Z]{6,}\b',  # chuỗi 6+ chữ cái Latin hoa liên tiếp
                                      '', addr).strip()
                        # Lưu ý: KHÔNG xóa "Viễn/Viên" vì là địa danh thật
                        # (Thị trấn Vĩnh Viễn, Long Mỹ, Hậu Giang)
                        # Xóa nhãn tiếng Việt còn sót
                        addr = re.sub(r'(?i)\bnơi\s*đăng\s*ký\b', '', addr).strip()
                        addr = re.sub(r'(?i)\bngày\s*sinh\s*[a-z]?\s*$', '', addr).strip()
                        addr = re.sub(r'(?i)^[a-z]\s+ngày\s*sinh', '', addr).strip()
                        addr = re.sub(r',\s*,', ',', addr)
                        addr = re.sub(r'\s{2,}', ' ', addr)
                            
                        # Tẩy sạch dấu phẩy thừa do nối chuỗi
                        data['Nơi thường trú gốc'] = re.sub(r',\s*,', ',', addr).lstrip(', ').rstrip('., ')
        
                    # --- BƯỚC 4.4: TRÍCH XUẤT GIỚI TÍNH (Chính xác từ dòng ghi Giới tính) ---
                    if "giới tính" in line_lower or "sex" in line_lower or "gioi tinh" in line_lower:
                        if "nữ" in line_lower or "nư" in line_lower or "nu" in line_lower:
                            data['Giới tính'] = 'Nữ'
                        elif "nam" in line_lower:
                            data['Giới tính'] = 'Nam'
        
                    # --- BƯỚC 4.5: TRÍCH XUẤT NGÀY CẤP ---
                    if ("ngày, tháng, năm" in line_lower or "date, month, year" in line_lower or "date of issue" in line_lower or "cấp" in line_lower or "ngay cap" in line_lower) and "sinh" not in line_lower and "hết hạn" not in line_lower and "expiry" not in line_lower and "birth" not in line_lower:
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

                # Hậu xử lý (Post-processing) làm sạch rác do OCR đọc lem viền
                if data.get('Họ tên'):
                    # Xoá các phụ âm đứng trơ trọi ở cuối tên do vết xước (VD: TRẦN NGỌC MUỘI T -> TRẦN NGỌC MUỘI)
                    data['Họ tên'] = re.sub(r'\s+[BCDGHKLMNPQRSTVX]$', '', data['Họ tên'], flags=re.IGNORECASE).strip()

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
                return {"CCCD": "", "CMND": "", "Họ tên": "", "Ngày sinh": "", "Giới tính": "", "Nơi thường trú gốc": "", "Ngày cấp CCCD": "", "OCR Side": ""}, "Không thể đọc file ảnh", None
        else:
            img_to_ocr = image_path_or_cv2img
            
    except Exception as e:
        return {}, f"Lỗi thư viện OCR: {str(e)}", None
        
    try:
        import cv2
        import numpy as np
        import warnings
        
        has_glare_warning = False
        
        def safe_extract_text(*args, **kwargs):
            nonlocal has_glare_warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = extract_text_from_image(*args, **kwargs)
                for warning in w:
                    if issubclass(warning.category, RuntimeWarning) and "invalid value encountered in divide" in str(warning.message):
                        has_glare_warning = True
                return result
        
        # --- PASS 1: TÌM CHIỀU ẢNH TỐT NHẤT ---
        best_img = img_to_ocr
        best_data = {'CCCD': '', 'Họ tên': '', 'Ngày sinh': '', 'OCR Side': '', 'Raw Text Upper': ''}
        best_note = "Ảnh mờ hoặc không thể nhận diện được"
        rotated_return = None
        
        text, is_vertical = safe_extract_text(img_to_ocr, return_orientation=True)
        data = parse_ocr_text(text)
        
        if data['CCCD'] or (not data['CCCD'] and data['OCR Side'] == 'Front' and data['Họ tên']):
            best_data = data
            if is_vertical:
                best_img = cv2.rotate(img_to_ocr, cv2.ROTATE_90_COUNTERCLOCKWISE)
                rotated_return = best_img
                # Cập nhật lại data cho ảnh đã xoay để chính xác hơn (đôi khi xoay lại đọc tốt hơn)
                text_rot, _ = safe_extract_text(best_img, return_orientation=True)
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
    addr_clean = re.sub(r',\s*-\s*', ' ', addr_raw) # Xóa ', -' (vd: KDC, - Hưng Phú 1 -> KDC Hưng Phú 1)
    addr_clean = re.sub(r',\s*,', ',', addr_clean) # Thay thế ', ,' hoặc ',,' bằng ','
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
    import json, time, re
    
    # Tiền xử lý: API VNHub rất nhạy cảm với khoảng trắng thừa, đặc biệt là khoảng trắng trước dấu phẩy
    # Ví dụ: "Số Nhà 137B , Trần Hưng Đạo ," -> lỗi data: []
    clean_addr = re.sub(r'\s+,', ',', addr)
    clean_addr = re.sub(r'\s+', ' ', clean_addr).strip()
    
    payload = json.dumps({"address": clean_addr})
    
    # Retry tối đa 50 lần đối với lỗi mạng/500
    # Retry tối đa 5 lần nếu API trả về thành công nhưng data = []
    empty_data_retries = 0
    max_empty_retries = 5
    
    for attempt in range(50):
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
            
            # API thành công nhưng data rỗng = không tìm thấy địa chỉ
            if empty_data_retries < max_empty_retries:
                empty_data_retries += 1
                time.sleep(2)
                continue
                
            # Đã thử 5 lần vẫn rỗng → từ bỏ
            return {
                "original": addr,
                "success": False,
                "error": "Không tìm thấy địa chỉ tương ứng"
            }
            
        except Exception as e:
            # Lỗi 500 hoặc mạng → thử lại sau 2s
            if attempt < 49:
                time.sleep(2)
                continue
            else:
                return {
                    "original": addr,
                    "success": False,
                    "error": f"Lỗi kết nối API sau 50 lần thử ({str(e)})"
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

console = Console()

def run_wizard(input_dir, normalize_address=True):
    from rich.text import Text
    file_logs = []
    
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
    
    # --- INCREMENTAL SCAN LOGIC ---
    incremental_scan = False
    old_records = []
    processed_images_set = set()
    max_renamed_idx = 0
    
    clean_input_dir = os.path.normpath(input_dir)
    possible_exports = [
        clean_input_dir + "_exports",
        os.path.join(clean_input_dir, "exports")
    ]
    
    all_old_excels = []
    for edir in possible_exports:
        if os.path.isdir(edir):
            all_old_excels.extend(glob.glob(os.path.join(edir, "*.xlsx")))
            
    latest_excel = None
    if all_old_excels:
        latest_excel = max(all_old_excels, key=os.path.getmtime)
        
    if latest_excel:
        incremental_scan = Confirm.ask(f"\n[bold yellow]Phát hiện thư mục này đã từng được xử lý (có file {os.path.basename(latest_excel)}). Bạn muốn QUÉT NỐI TIẾP (chỉ quét ảnh mới ném vào) không? (Chọn No để quét lại từ đầu)[/bold yellow]", default=True)
    elif os.path.exists(os.path.join(input_dir, "original.zip")):
        excel_path = Prompt.ask("\n[bold yellow]Phát hiện thư mục này đã từng được xử lý (có file original.zip) nhưng không tìm thấy file Excel cũ.\n👉 Nếu bạn muốn QUÉT NỐI TIẾP, vui lòng copy đường dẫn file Excel cũ dán vào đây (hoặc nhấn Enter để quét lại toàn bộ ảnh từ đầu)[/bold yellow]").strip().strip('\'"')
        if excel_path and os.path.isfile(excel_path) and excel_path.endswith('.xlsx'):
            latest_excel = excel_path
            incremental_scan = True

    if incremental_scan and latest_excel:
        console.print(f"[cyan]Đang đọc file Excel cũ ({os.path.basename(latest_excel)}) để lọc ra các ảnh mới...[/cyan]")
        try:
            wb = openpyxl.load_workbook(latest_excel)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            col_idx = {name: i for i, name in enumerate(headers)}
            
            img_front_col = col_idx.get('Ảnh mặt trước CCCD/CC')
            img_back_col = col_idx.get('Ảnh mặt sau CCCD/CC')
            renamed_front_col = col_idx.get('Đổi tên Ảnh mặt trước CCCD/CC')
            renamed_back_col = col_idx.get('Đổi tên Ảnh mặt sau CCCD/CC')
            
            if img_front_col is None or img_back_col is None:
                console.print("[red]❌ File Excel cũ không có cột tên ảnh, không thể quét nối tiếp.[/red]")
                incremental_scan = False
            else:
                for row in ws.iter_rows(min_row=2, values_only=True):
                    old_records.append({
                        'Họ tên': row[col_idx.get('Họ tên')] if 'Họ tên' in col_idx else '',
                        'CCCD': row[col_idx.get('CCCD')] if 'CCCD' in col_idx else '',
                        'CMND': row[col_idx.get('CMND')] if 'CMND' in col_idx else '',
                        'Giới tính': row[col_idx.get('Giới tính')] if 'Giới tính' in col_idx else '',
                        'Ngày sinh': row[col_idx.get('Ngày sinh')] if 'Ngày sinh' in col_idx else '',
                        'Nơi thường trú gốc': row[col_idx.get('Nơi thường trú gốc')] if 'Nơi thường trú gốc' in col_idx else '',
                        'Địa chỉ chuẩn hóa mới': row[col_idx.get('Địa chỉ chuẩn hóa mới')] if 'Địa chỉ chuẩn hóa mới' in col_idx else '',
                        'Ngày cấp CCCD': row[col_idx.get('Ngày cấp CCCD')] if 'Ngày cấp CCCD' in col_idx else '',
                        'Nơi cấp': row[col_idx.get('Nơi cấp')] if 'Nơi cấp' in col_idx else '',
                        'Ngày hết hạn': row[col_idx.get('Ngày hết hạn')] if 'Ngày hết hạn' in col_idx else '',
                        'Phân loại': row[col_idx.get('Phân loại')] if 'Phân loại' in col_idx else '',
                        'Ghi chú': row[col_idx.get('Ghi chú')] if 'Ghi chú' in col_idx else '',
                        'QR Raw': row[col_idx.get('QR Raw')] if 'QR Raw' in col_idx else '',
                        'Ảnh mặt trước CCCD/CC': row[img_front_col],
                        'Ảnh mặt sau CCCD/CC': row[img_back_col],
                        'Đổi tên Ảnh mặt trước CCCD/CC': row[renamed_front_col] if renamed_front_col is not None else '',
                        'Đổi tên Ảnh mặt sau CCCD/CC': row[renamed_back_col] if renamed_back_col is not None else ''
                    })
                    front = row[img_front_col]
                    back = row[img_back_col]
                    
                    if front: processed_images_set.add(str(front))
                    if back: processed_images_set.add(str(back))
                    
        except Exception as e:
            console.print(f"[red]❌ Lỗi đọc file Excel cũ: {e}[/red]")
            incremental_scan = False
                    
    if incremental_scan:
        new_image_paths = [p for p in image_paths if os.path.basename(p) not in processed_images_set]
        
        for p in image_paths:
            base = os.path.splitext(os.path.basename(p))[0]
            if base.isdigit() and int(base) > max_renamed_idx:
                max_renamed_idx = int(base)
                
        new_image_paths = [p for p in new_image_paths if not os.path.splitext(os.path.basename(p))[0].isdigit()]
        
        if not new_image_paths:
            console.print("\n[bold green]✅ Không tìm thấy ảnh mới nào được chép thêm vào. Kết thúc quá trình quét nối tiếp![/bold green]")
            return
        console.print(f"[bold green]✅ Đã tự động lọc ra [yellow]{len(new_image_paths)}[/yellow] ảnh mới cần xử lý.[/bold green]")
        image_paths = new_image_paths

    # --- AUTO BACKUP AND RENAME LOGIC ---
    zip_path = os.path.join(input_dir, "original.zip")
    
    if not os.path.exists(zip_path) or incremental_scan:
        action_word = "bổ sung" if incremental_scan else "gốc"
        mode = 'a' if incremental_scan else 'w'
        start_idx = max_renamed_idx + 1 if incremental_scan else 1
        
        console.print(f"[cyan]📦 Đang nén {action_word} các file ảnh vào original.zip...[/cyan]")
        try:
            with zipfile.ZipFile(zip_path, mode, zipfile.ZIP_DEFLATED) as zipf:
                for file_path in image_paths:
                    zipf.write(file_path, os.path.basename(file_path))
            
            if incremental_scan:
                console.print(f"[cyan]🔄 Đang đổi tên các file ảnh mới nối tiếp (từ số {start_idx})...[/cyan]")
            else:
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
            for i, (temp_path, ext) in enumerate(temp_paths, start_idx):
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

    api_threads = 4
    if normalize_address:
        api_threads_input = Prompt.ask("[cyan]Nhập số luồng gọi API địa chỉ song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
        try:
            api_threads = int(api_threads_input) if api_threads_input else 4
        except ValueError:
            console.print("[yellow]Số luồng không hợp lệ, dùng mặc định 4[/yellow]")
            api_threads = 4

    # Wizard confirmation
    confirm = Confirm.ask("\n[bold yellow]Bạn có muốn bắt đầu xử lý ngay bây giờ không?[/bold yellow]", default=True)
    if not confirm:
        console.print("[yellow]Đã hủy quá trình.[/yellow]")
        return

    console.print("\n")
    console.print(Panel(f"[bold cyan]🚀 BẮT ĐẦU XỬ LÝ {len(image_paths)} ẢNH VỚI {num_threads} LUỒNG...[/bold cyan]", border_style="green"))

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
                
                # Use lock for thread safety because deep learning models (PyTorch/ONNX) inside extract_ocr_data
                # might cause Segmentation Faults when run concurrently across multiple threads in the same process.
                with ocr_lock:
                    ocr_data, ocr_note, rotated_img = extract_ocr_data(img)
                
                if rotated_img is not None:
                    # Lưu lại ảnh đã xoay chuẩn vào thư mục tạm thay vì ghi đè file gốc
                    temp_path = os.path.join(temp_rotated_dir, os.path.basename(img_path))
                    cv2.imwrite(temp_path, rotated_img)
                    row_data['Full Image Path'] = temp_path
                
                # In thông tin OCR ra màn hình tùy theo mặt thẻ
                parts = []
                side = ocr_data.get('OCR Side')
                if side: parts.append(f"[{side}]")
                parts.append(f"CCCD: {ocr_data.get('CCCD') or '[Trống]'}")
                parts.append(f"Tên: {ocr_data.get('Họ tên') or '[Trống]'}")
                
                if side == 'Front':
                    parts.append(f"NS: {ocr_data.get('Ngày sinh') or '[Trống]'}")
                    addr = ocr_data.get('Nơi thường trú gốc') or '[Trống]'
                    parts.append(f"Địa chỉ: {addr}")
                    if ocr_data.get('Ngày cấp CCCD'):
                        parts.append(f"Ngày cấp: {ocr_data.get('Ngày cấp CCCD')}")
                elif side == 'Back':
                    parts.append(f"Ngày cấp: {ocr_data.get('Ngày cấp CCCD') or '[Trống]'}")
                else:
                    # Nếu không xác định được mặt, in tất cả
                    parts.append(f"NS: {ocr_data.get('Ngày sinh') or '[Trống]'}")
                    parts.append(f"Ngày cấp: {ocr_data.get('Ngày cấp CCCD') or '[Trống]'}")
                
                ocr_print_info = ", ".join(parts)
                log_msgs.append(f"[blue]ℹ️ Kết quả OCR:[/blue] {ocr_print_info} | Note: {ocr_note}")
                
                if DEBUG_MODE and ocr_data.get('Raw Text'):
                    log_msgs.append(f"[magenta]🐛 DEBUG RAW OCR TEXT:\n{ocr_data['Raw Text']}[/magenta]")
                
                # In ra màn hình cảnh báo chói lóa nếu có
                if "chói/lóa" in ocr_note:
                    log_msgs.append(f"[red]⚠️ Ảnh bị chói/lóa sáng hoặc quá mờ không thể xử lý tốt[/red]")
                
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
                    file_logs.append(f"[{os.path.basename(img_path)}]")
                    for msg in log_msgs:
                        progress.console.print(f"  {msg}")
                        file_logs.append("  " + Text.from_markup(msg).plain)
                except Exception as exc:
                    err = f"❌ Lỗi khi xử lý ảnh {os.path.basename(img_path)}: {exc}"
                    progress.console.print(f"[bold red]{err}[/bold red]")
                    file_logs.append(err)
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
                'has_ocr_data': False,
                'has_cong_dan_front': False,
                'has_address_front': False,
                'has_address_back': False,
                'has_cuc_truong_back': False,
                'has_bo_cong_an_back': False
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
                
            raw_text = item.get('Raw Text Upper', '')
            if item.get('OCR Side') == 'Front':
                record['OCR Image Path Front'] = item['Image Path']
                record['Full OCR Image Path Front'] = item['Full Image Path']
                if "CÔNG DÂN" in raw_text: record['has_cong_dan_front'] = True
                if item.get('Nơi thường trú gốc'): record['has_address_front'] = True
            elif item.get('OCR Side') == 'Back':
                record['OCR Image Path Back'] = item['Image Path']
                record['Full OCR Image Path Back'] = item['Full Image Path']
                if "CỤC TRƯỞNG" in raw_text: record['has_cuc_truong_back'] = True
                if "BỘ CÔNG AN" in raw_text: record['has_bo_cong_an_back'] = True
                if item.get('Nơi thường trú gốc'): record['has_address_back'] = True
            else:
                record['OCR Image Path Unknown'] = item['Image Path']
                record['Full OCR Image Path Unknown'] = item['Full Image Path']
            
            if item.get('Ghi chú'):
                record['Ghi chú'].append(item['Ghi chú'])

    # ---------- FUZZY MATCH: GỘP MẶT SAU OCR VÀO ĐÚNG BẢN GHI (2/3 TRƯỜNG) ----------
    # Mặt sau quét bằng OCR có thể đọc sai CCCD (ví dụ: 086... → 080...)
    # Nếu 2/3 trong {CCCD, Họ tên không dấu, Ngày cấp} khớp với bản ghi đã có → ghép vào đó
    import unicodedata

    def _norm_for_match(text):
        """Chuẩn hóa để so khớp: xóa dấu, in hoa, rút gọn khoảng trắng."""
        if not text: return ''
        text = text.upper().strip()
        nfkd = unicodedata.normalize('NFKD', text)
        return ' '.join(''.join(c for c in nfkd if not unicodedata.combining(c)).split())

    # Tìm các bản ghi "mặt sau mồ côi": chỉ có OCR Back, không có QR, không có mặt trước
    orphan_cccds = [
        cccd for cccd, rec in records.items()
        if (not rec['has_qr_data']
            and (rec.get('OCR Image Path Back') or rec.get('Full OCR Image Path Back'))
            and not rec.get('Full Image Path Front')
            and not rec.get('OCR Image Path Front'))
    ]

    for orphan_cccd in orphan_cccds:
        orphan = records[orphan_cccd]
        o_cccd = orphan.get('CCCD', '')
        o_name = _norm_for_match(orphan.get('Họ tên', ''))
        o_date = orphan.get('Ngày cấp CCCD', '')

        best_cccd = None
        for r_cccd, r_rec in records.items():
            if r_cccd == orphan_cccd:
                continue
            # Chỉ so với bản ghi đã có mặt trước hoặc QR
            if not (r_rec['has_qr_data']
                    or r_rec.get('Full Image Path Front')
                    or r_rec.get('OCR Image Path Front')):
                continue
            r_name = _norm_for_match(r_rec.get('Họ tên', ''))
            r_date = r_rec.get('Ngày cấp CCCD', '')

            score = 0
            if o_cccd and o_cccd == r_cccd:              score += 1
            if o_name and r_name and o_name == r_name:   score += 1
            if o_date and r_date and o_date == r_date:   score += 1
            if score >= 2:
                best_cccd = r_cccd
                break

        # Tùy chọn 2: Nếu chưa tìm được, kiểm tra 8 số liên tiếp hoặc khớp ngày cấp cho bản ghi đang thiếu mặt sau
        if not best_cccd:
            for r_cccd, r_rec in records.items():
                if r_cccd == orphan_cccd:
                    continue
                if not (r_rec['has_qr_data']
                        or r_rec.get('Full Image Path Front')
                        or r_rec.get('OCR Image Path Front')):
                    continue
                # Bản ghi đích phải thiếu mặt sau
                if r_rec.get('OCR Image Path Back') or r_rec.get('Full OCR Image Path Back') or r_rec.get('Ảnh mặt sau CCCD/CC') or r_rec.get('Full Image Path Back'):
                    continue
                
                match_8_digits = False
                if len(o_cccd) >= 8 and len(r_cccd) >= 8:
                    for i in range(len(r_cccd) - 7):
                        if r_cccd[i:i+8] in o_cccd:
                            match_8_digits = True
                            break
                            
                r_date = r_rec.get('Ngày cấp CCCD', '')
                match_date = (o_date and r_date and o_date == r_date)
                
                if match_8_digits or match_date:
                    best_cccd = r_cccd
                    break

        if best_cccd:
            target = records[best_cccd]
            # Ghép back-side image vào bản ghi đúng
            if not target.get('OCR Image Path Back'):
                target['OCR Image Path Back'] = orphan.get('OCR Image Path Back', '')
            if not target.get('Full OCR Image Path Back'):
                target['Full OCR Image Path Back'] = orphan.get('Full OCR Image Path Back', '')
            # Bổ sung thông tin còn thiếu từ OCR mặt sau
            for k in ['Họ tên', 'Ngày cấp CCCD']:
                if orphan.get(k) and not target.get(k):
                    target[k] = orphan[k]
            console.print(
                f"   [bold green]→ [FUZZY MATCH][/bold green] Ghép mặt sau (CCCD OCR: {orphan_cccd}) "
                f"vào bản ghi {best_cccd} (khớp 2/3 trường: tên/ngày cấp/cccd)."
            )
            del records[orphan_cccd]

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
    address_map = {}

    # Gọi API chuẩn hóa địa chỉ theo batch, advance progress bar theo từng kết quả
    if normalize_address and unique_addresses:
        console.print(Panel(f"[bold cyan]🌐 ĐANG CHUẨN BỊ GỌI API CHUẨN HÓA CHO {len(unique_addresses)} ĐỊA CHỈ DUY NHẤT VỚI {api_threads} LUỒNG...[/bold cyan]", border_style="green"))
        batch_size = 100
        total_addrs = len(unique_addresses)
        processed_count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[bold]{task.fields[status]}"),
            TimeElapsedColumn(),
            console=console,
        ) as api_progress:
            api_task = api_progress.add_task(
                "[cyan]Đang chuẩn hóa địa chỉ...",
                total=total_addrs,
                status=""
            )
            
            for i in range(0, total_addrs, batch_size):
                batch = unique_addresses[i:i+batch_size]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=api_threads) as executor:
                    future_to_addr = {executor.submit(fetch_single_address, addr): addr for addr in batch}
                    for future in concurrent.futures.as_completed(future_to_addr):
                        result = future.result()
                        processed_count += 1
                        if result and 'original' in result:
                            orig_addr = result['original']
                            address_map[orig_addr] = result
                            short_addr = orig_addr[:45]
                            
                            if result.get('success'):
                                new_addr = result.get('converted', '')
                                status_text = f"[green]✓[/green] {short_addr}"
                                api_progress.console.print(f"[bold cyan][{processed_count}/{total_addrs}][/bold cyan] [dim]Từ:[/dim] [yellow]{orig_addr}[/yellow]\n{' '*(len(str(total_addrs))*2 + 5)}[dim]→  [/dim] [bold green]{new_addr}[/bold green]")
                            else:
                                err_msg = result.get('error', 'Lỗi không xác định')
                                status_text = f"[red]✗[/red] {short_addr}"
                                api_progress.console.print(f"[bold cyan][{processed_count}/{total_addrs}][/bold cyan] [dim]Từ:[/dim] [yellow]{orig_addr}[/yellow]\n{' '*(len(str(total_addrs))*2 + 5)}[dim]→  [/dim] [bold red]{err_msg}[/bold red]")
                                
                            api_progress.update(api_task, advance=1, status=status_text)

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
            
        if not record.get('QR Raw'):
            if record['has_cong_dan_front'] or record['has_address_front'] or record['has_cuc_truong_back']:
                record['Phân loại'] = 'Căn cước công dân'
            elif record['has_address_back'] and not record['has_cong_dan_front'] and record['has_bo_cong_an_back']:
                record['Phân loại'] = 'Căn cước'
            else:
                record['Phân loại'] = 'Khác'
                
        # Tự động suy luận Nơi cấp dựa vào Phân loại (dành cho các thẻ hỏng QR)
        if not record.get('Nơi cấp'):
            if record['Phân loại'] == 'Căn cước công dân':
                record['Nơi cấp'] = 'CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI'
            elif record['Phân loại'] == 'Căn cước':
                record['Nơi cấp'] = 'BỘ CÔNG AN'
                
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

    if 'incremental_scan' in locals() and incremental_scan and old_records:
        processed_data = old_records + processed_data

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
            
    timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
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

    # --- Sheet "Review": dòng dữ liệu chưa đầy đủ thông tin ---
    REQUIRED_FIELDS = ['Họ tên', 'Ngày sinh', 'Nơi thường trú gốc', 'Ngày cấp CCCD',
                       'Ảnh mặt trước CCCD/CC', 'Ảnh mặt sau CCCD/CC']
    review_rows = []
    for row in processed_data:
        missing = [f for f in REQUIRED_FIELDS if not row.get(f)]
        if missing:
            review_rows.append((row, missing))

    ws_review = wb.create_sheet(title="Review")
    ws_review.append(["STT", "CCCD", "Họ tên", "Ảnh mặt trước", "Ảnh mặt sau", "Trường còn thiếu"])
    for cell in ws_review[1]:
        cell.font = Font(bold=True)
    for stt, (row, missing) in enumerate(review_rows, 1):
        ws_review.append([
            stt,
            row.get('CCCD', ''),
            row.get('Họ tên', ''),
            row.get('Ảnh mặt trước CCCD/CC', ''),
            row.get('Ảnh mặt sau CCCD/CC', ''),
            ', '.join(missing)
        ])
    for col in ws_review.columns:
        ws_review.column_dimensions[col[0].column_letter].width = 30

    # --- Sheet "Unknown": ảnh không thuộc dòng nào (không đọc được CCCD) ---
    all_matched_paths = set()
    for row in processed_data:
        if row.get('Full Image Path Front'): all_matched_paths.add(row['Full Image Path Front'])
        if row.get('Full Image Path Back'): all_matched_paths.add(row['Full Image Path Back'])

    unknown_image_paths = [p for p in image_paths if p not in all_matched_paths]

    ws_unknown = wb.create_sheet(title="Unknown")
    ws_unknown.append(["STT", "Tên file gốc"])
    for cell in ws_unknown[1]:
        cell.font = Font(bold=True)
    for stt, fpath in enumerate(unknown_image_paths, 1):
        ws_unknown.append([stt, os.path.basename(fpath)])
    for col in ws_unknown.columns:
        ws_unknown.column_dimensions[col[0].column_letter].width = 40

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

    # 3. review.zip: ảnh của các dòng chưa đầy đủ thông tin
    review_image_paths = []
    added_review = set()
    for row, _ in review_rows:
        for field in ['Full Image Path Front', 'Full Image Path Back']:
            p = row.get(field)
            if p and p not in added_review:
                review_image_paths.append(p)
                added_review.add(p)
    create_zip_helper('review.zip', review_image_paths)

    # 4. unknown.zip: ảnh không thuộc dòng nào
    create_zip_helper('unknown.zip', unknown_image_paths)
    
    console.print("\n" + "🎉"*15)
    console.print(f"[bold green]ĐÃ HOÀN TẤT THÀNH CÔNG![/bold green]")
    console.print(f"File kết quả được lưu tại: [yellow]{os.path.abspath(output_filename)}[/yellow]")
    
    # Xuất file log
    log_filename = os.path.join(exports_dir, f"log_{timestamp}.txt")
    file_logs.append("\nĐÃ HOÀN TẤT THÀNH CÔNG!")
    file_logs.append(f"File kết quả: {os.path.abspath(output_filename)}")
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(file_logs))
    console.print(f"File log chi tiết được lưu tại: [yellow]{os.path.abspath(log_filename)}[/yellow]")
    console.print("🎉"*15 + "\n")

def run_reprocess(excel_path, normalize_address=True):
    from rich.text import Text
    import datetime
    file_logs = []
    
    excel_dir = os.path.dirname(os.path.abspath(excel_path))
    parent_dir = os.path.dirname(excel_dir)
    image_dir = parent_dir
    
    user_img_dir = Prompt.ask(f"[bold cyan]Nhập đường dẫn thư mục chứa ảnh gốc (Ấn Enter nếu là: {image_dir})[/bold cyan]").strip().strip('\'"')
    if user_img_dir:
        image_dir = user_img_dir
        
    if not os.path.isdir(image_dir):
        console.print(f"[bold red]❌ Thư mục ảnh '{image_dir}' không tồn tại![/bold red]")
        return
        
    image_paths = []
    for ext in ('*.jpg', '*.jpeg', '*.png', '*.heic', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.HEIC', '*.WEBP'):
        image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
        
    img_map = {os.path.basename(p): p for p in image_paths}
    
    console.print(f"[cyan]Đang đọc file Excel: {excel_path}[/cyan]")
    try:
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi đọc file Excel: {e}[/bold red]")
        return
        
    headers = [cell.value for cell in ws[1]]
    if not headers or "Họ tên" not in headers:
        console.print("[bold red]❌ File Excel không đúng định dạng (không tìm thấy cột 'Họ tên').[/bold red]")
        return
        
    col_idx = {name: i for i, name in enumerate(headers)}
    
    required_cols = ['Họ tên', 'CCCD', 'Ngày sinh', 'Nơi thường trú gốc', 'Ngày cấp CCCD', 'Nơi cấp', 'Ngày hết hạn']
    img_front_col = col_idx.get('Ảnh mặt trước CCCD/CC')
    img_back_col = col_idx.get('Ảnh mặt sau CCCD/CC')
    
    if img_front_col is None or img_back_col is None:
        console.print("[bold red]❌ Không tìm thấy cột chứa tên file ảnh trong Excel.[/bold red]")
        return

    rows_to_process = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        is_missing = False
        for col_name in required_cols:
            idx = col_idx.get(col_name)
            if idx is not None:
                val = row[idx].value
                if not val or str(val).strip() == "" or str(val).strip() == "None":
                    is_missing = True
                    break
        if is_missing:
            front_name = row[img_front_col].value
            back_name = row[img_back_col].value
            rows_to_process.append({
                'row_idx': row_idx,
                'front_name': front_name,
                'back_name': back_name,
                'row_cells': row
            })
            
    if not rows_to_process:
        console.print("[bold green]✅ Tất cả các dòng trong file Excel đều đã đầy đủ thông tin, không cần xử lý lại![/bold green]")
        return
        
    console.print(f"[bold yellow]⚠️ Tìm thấy {len(rows_to_process)} dòng bị thiếu thông tin cần xử lý lại.[/bold yellow]")
    
    # Cấu hình luồng xử lý
    num_threads_input = Prompt.ask("\n[cyan]Nhập số luồng xử lý ảnh song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
    try:
        num_threads = int(num_threads_input) if num_threads_input else 4
    except ValueError:
        console.print("[yellow]⚠️ Giá trị không hợp lệ, sử dụng mặc định: 4 luồng.[/yellow]")
        num_threads = 4

    api_threads = 4
    if normalize_address:
        api_threads_input = Prompt.ask("[cyan]Nhập số luồng gọi API địa chỉ song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
        try:
            api_threads = int(api_threads_input) if api_threads_input else 4
        except ValueError:
            console.print("[yellow]Số luồng không hợp lệ, dùng mặc định 4[/yellow]")
            api_threads = 4
        
    confirm = Confirm.ask("\n[bold yellow]Bạn có muốn bắt đầu TÁI XỬ LÝ ngay bây giờ không?[/bold yellow]", default=True)
    if not confirm:
        console.print("[yellow]Đã hủy quá trình.[/yellow]")
        return
    
    # Process images for missing rows
    import concurrent.futures
    
    # Helper to reprocess a single image
    def process_single_image(img_path):
        qr_string, engine, err, img, qr_rotated_img = extract_qr_data(img_path)
        log_msgs = []
        row_data = {}
        if qr_string:
            log_msgs.append(f"[green]✅ [Đã quét mã QR bằng {engine}]:[/green] {qr_string}")
            extracted, validation_notes = process_qr_string(qr_string)
            row_data.update(extracted)
        else:
            if img is not None:
                log_msgs.append(f"[yellow]⚠️ Không đọc được QR, đang thử quét OCR...[/yellow]")
                with ocr_lock:
                    ocr_data, ocr_note, rotated_img = extract_ocr_data(img)
                
                parts = []
                side = ocr_data.get('OCR Side')
                if side: parts.append(f"[{side}]")
                parts.append(f"CCCD: {ocr_data.get('CCCD') or '[Trống]'}")
                parts.append(f"Tên: {ocr_data.get('Họ tên') or '[Trống]'}")
                
                ocr_print_info = ", ".join(parts)
                log_msgs.append(f"[blue]ℹ️ Kết quả OCR:[/blue] {ocr_print_info} | Note: {ocr_note}")
                
                if DEBUG_MODE and ocr_data.get('Raw Text'):
                    log_msgs.append(f"[magenta]🐛 DEBUG RAW OCR TEXT:\n{ocr_data['Raw Text']}[/magenta]")
                
                row_data.update(ocr_data)
        
        row_data['Nơi cấp'] = get_place_of_issue(row_data.get('QR Raw', ''))
        row_data['Ngày hết hạn'] = calculate_expiry_date(row_data.get('Ngày sinh', ''))
        return row_data, log_msgs

    # We need to process both front and back images for each row
    all_images_to_process = set()
    for row in rows_to_process:
        if row['front_name'] and row['front_name'] in img_map:
            all_images_to_process.add(img_map[row['front_name']])
        if row['back_name'] and row['back_name'] in img_map:
            all_images_to_process.add(img_map[row['back_name']])
            
    img_results = {}
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Đang quét ảnh...", total=len(all_images_to_process))
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_img = {executor.submit(process_single_image, path): path for path in all_images_to_process}
            for future in concurrent.futures.as_completed(future_to_img):
                img_path = future_to_img[future]
                try:
                    row_data, log_msgs = future.result()
                    img_results[img_path] = row_data
                    
                    progress.console.print(f"[bold][{os.path.basename(img_path)}][/bold]")
                    file_logs.append(f"[{os.path.basename(img_path)}]")
                    for msg in log_msgs:
                        progress.console.print(f"  {msg}")
                        file_logs.append("  " + Text.from_markup(msg).plain)
                except Exception as exc:
                    err = f"❌ Lỗi khi xử lý ảnh {os.path.basename(img_path)}: {exc}"
                    progress.console.print(f"[bold red]{err}[/bold red]")
                    file_logs.append(err)
                finally:
                    progress.advance(task_id)

    # Merge results back into Excel rows
    # We prioritize keeping existing non-empty values, but overwrite if OCR found new data
    address_to_normalize = set()
    for row_info in rows_to_process:
        front_path = img_map.get(row_info['front_name']) if row_info['front_name'] else None
        back_path = img_map.get(row_info['back_name']) if row_info['back_name'] else None
        
        front_data = img_results.get(front_path, {})
        back_data = img_results.get(back_path, {})
        
        # Merge logic
        for col_name in required_cols:
            idx = col_idx.get(col_name)
            if idx is None: continue
            
            existing_val = row_info['row_cells'][idx].value
            if existing_val and str(existing_val).strip() != "" and str(existing_val).strip() != "None":
                continue # Giữ nguyên giá trị cũ nếu đã có
                
            # Cố lấy từ front_data hoặc back_data
            new_val = front_data.get(col_name) or back_data.get(col_name)
            if new_val:
                row_info['row_cells'][idx].value = new_val
                
                # Nếu là địa chỉ, gom để gửi API chuẩn hóa
                if col_name == 'Nơi thường trú gốc' and new_val:
                    address_to_normalize.add(new_val)

    # Nơi chuẩn hóa địa chỉ
    if normalize_address and address_to_normalize:
        console.print(Panel(f"[bold cyan]🌐 ĐANG CHUẨN BỊ GỌI API CHUẨN HÓA CHO {len(address_to_normalize)} ĐỊA CHỈ DUY NHẤT VỚI {api_threads} LUỒNG...[/bold cyan]", border_style="green"))
        address_map = {}
        unique_addresses = list(address_to_normalize)
        batch_size = 100
        total_addrs = len(unique_addresses)
        processed_count = 0
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), TaskProgressColumn(), TextColumn("[bold]{task.fields[status]}"),
            TimeElapsedColumn(), console=console,
        ) as api_progress:
            api_task = api_progress.add_task("[cyan]Đang chuẩn hóa địa chỉ...", total=total_addrs, status="")
            for i in range(0, total_addrs, batch_size):
                batch = unique_addresses[i:i+batch_size]
                with concurrent.futures.ThreadPoolExecutor(max_workers=api_threads) as executor:
                    future_to_addr = {executor.submit(fetch_single_address, addr): addr for addr in batch}
                    for future in concurrent.futures.as_completed(future_to_addr):
                        result = future.result()
                        processed_count += 1
                        if result and 'original' in result:
                            orig_addr = result['original']
                            address_map[orig_addr] = result
                            short_addr = orig_addr[:45]
                            if result.get('success'):
                                new_addr = result.get('converted', '')
                                status_text = f"[green]✓[/green] {short_addr}"
                                api_progress.console.print(f"[bold cyan][{processed_count}/{total_addrs}][/bold cyan] [dim]Từ:[/dim] [yellow]{orig_addr}[/yellow]\n{' '*(len(str(total_addrs))*2 + 5)}[dim]→  [/dim] [bold green]{new_addr}[/bold green]")
                            else:
                                err_msg = result.get('error', 'Lỗi không xác định')
                                status_text = f"[red]✗[/red] {short_addr}"
                                api_progress.console.print(f"[bold cyan][{processed_count}/{total_addrs}][/bold cyan] [dim]Từ:[/dim] [yellow]{orig_addr}[/yellow]\n{' '*(len(str(total_addrs))*2 + 5)}[dim]→  [/dim] [bold red]{err_msg}[/bold red]")
                            api_progress.update(api_task, advance=1, status=status_text)
                            
        # Điền lại địa chỉ chuẩn hóa vào Excel
        norm_idx = col_idx.get('Địa chỉ chuẩn hóa mới')
        orig_idx = col_idx.get('Nơi thường trú gốc')
        if norm_idx is not None and orig_idx is not None:
            for row_info in rows_to_process:
                orig_val = row_info['row_cells'][orig_idx].value
                if orig_val and orig_val in address_map and address_map[orig_val].get('success'):
                    # Đè lên luôn vì mình vừa reprocess
                    row_info['row_cells'][norm_idx].value = address_map[orig_val].get('converted', '')

    timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
    reprocess_out = excel_path.replace('.xlsx', f'_reprocessed_{timestamp}.xlsx')
    wb.save(reprocess_out)
    
    log_filename = excel_path.replace('.xlsx', f'_reprocess_log_{timestamp}.txt')
    file_logs.append("\nĐÃ HOÀN TẤT THÀNH CÔNG TÁI XỬ LÝ!")
    file_logs.append(f"File kết quả: {os.path.abspath(reprocess_out)}")
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(file_logs))
        
    console.print("\n" + "🎉"*15)
    console.print(f"[bold green]ĐÃ HOÀN TẤT THÀNH CÔNG TÁI XỬ LÝ![/bold green]")
    console.print(f"File kết quả được lưu tại: [yellow]{os.path.abspath(reprocess_out)}[/yellow]")
    console.print(f"File log chi tiết được lưu tại: [yellow]{os.path.abspath(log_filename)}[/yellow]")
    console.print("🎉"*15 + "\n")


def main():
    console.print(Panel.fit("[bold green]🚀 PHẦN MỀM TRÍCH XUẤT MÃ QR TỪ ẢNH CCCD RA EXCEL[/bold green]", border_style="cyan", padding=(1, 5)))
    
    with console.status("[bold green]Đang khởi tạo model AI...", spinner="dots"):
        init_models()
        
    first_run = True

    while True:
        input_dir = ""
        do_normalize = True
        # Bỏ tham số --debug khỏi sys.argv để không bị nhầm thành thư mục đầu vào
        args = [a for a in sys.argv if a != '--debug']
        if first_run and len(args) >= 2:
            input_dir = args[1]
            first_run = False
            if input_dir.endswith('.xlsx') and os.path.isfile(input_dir):
                run_reprocess(input_dir, normalize_address=True)
                if not Confirm.ask("\n[bold yellow]Bạn có muốn tiếp tục xử lý thư mục khác không?[/bold yellow]"):
                    console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
                    break
                continue
            else:
                run_wizard(input_dir, normalize_address=True)
        else:
            is_reprocess = Confirm.ask("\n[bold yellow]Bạn có muốn TÁI XỬ LÝ (chỉ quét lại các ảnh cũ bị lỗi/thiếu thông tin trong file Excel) không?\n👉 Chọn 'n' (No) nếu bạn muốn quét Thư mục mới hoặc Quét nối tiếp ảnh mới.[/bold yellow]", default=False)
            global DEBUG_MODE
            
            if is_reprocess:
                excel_path = Prompt.ask("[bold cyan]Nhập đường dẫn file Excel cũ (hoặc gõ 'q' để thoát)[/bold cyan]").strip().strip('\'"')
                if excel_path.lower() in ('q', 'quit', 'exit'):
                    console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
                    break
                if not os.path.isfile(excel_path) or not excel_path.endswith('.xlsx'):
                    console.print(f"\n[bold red]❌ Lỗi: File '{excel_path}' không hợp lệ hoặc không tồn tại.[/bold red]")
                    continue
                    
                if not DEBUG_MODE:
                    if Confirm.ask("[bold yellow]Bạn có muốn bật chế độ Gỡ lỗi (ghi toàn bộ Raw OCR Text vào file log) không?[/bold yellow]", default=False):
                        DEBUG_MODE = True
                do_normalize = Confirm.ask("\n[bold yellow]Bạn có muốn KIỂM TRA & CHUẨN HÓA ĐỊA CHỈ (quá trình này cần kết nối mạng) không?[/bold yellow]", default=True)
                
                run_reprocess(excel_path, normalize_address=do_normalize)
            else:
                console.print("\n[yellow][Hướng dẫn][/yellow]: Kéo thả thư mục chứa ảnh vào cửa sổ này, hoặc copy đường dẫn thư mục và dán vào đây.")
                input_dir = Prompt.ask("[bold cyan]Nhập đường dẫn thư mục chứa ảnh CCCD (hoặc gõ 'q' để thoát)[/bold cyan]").strip().strip('\'"')
                
                if input_dir.lower() in ('q', 'quit', 'exit'):
                    console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
                    break
                    
                if not DEBUG_MODE:
                    if Confirm.ask("[bold yellow]Bạn có muốn bật chế độ Gỡ lỗi (ghi toàn bộ Raw OCR Text vào file log) không?[/bold yellow]", default=False):
                        DEBUG_MODE = True
                        
                do_normalize = Confirm.ask("\n[bold yellow]Bạn có muốn KIỂM TRA & CHUẨN HÓA ĐỊA CHỈ (quá trình này cần kết nối mạng và tốn thêm thời gian) không?[/bold yellow]", default=True)
                
                run_wizard(input_dir, normalize_address=do_normalize)
                
            first_run = False
        
        if not Confirm.ask("\n[bold yellow]Bạn có muốn tiếp tục xử lý thư mục khác không?[/bold yellow]"):
            console.print("\n[bold green]Cảm ơn bạn đã sử dụng phần mềm. Tạm biệt![/bold green]")
            break

if __name__ == '__main__':
    main()
