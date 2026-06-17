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
                        return res.text, "zxing-cpp"
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
                txt = decoded_objects[0].data.decode('utf-8')
                if '|' in txt and len(txt.split('|')) >= 6:
                    if not re.search(r'[^\x00-\x7FÀ-ỹ\s\|\:\-/\.]', txt):
                        return txt, "pyzbar"

            # 3. wechat_qrcode
            global detector
            if detector:
                try:
                    res, _ = detector.detectAndDecode(scan_img)
                    if res and len(res) > 0:
                        txt = res[0]
                        if '|' in txt and len(txt.split('|')) >= 6:
                            if not re.search(r'[^\x00-\x7FÀ-ỹ\s\|\:\-/\.]', txt):
                                return txt, "WeChat QRCode"
                except Exception:
                    pass
            
            return None, None

        # 1. Quét toàn bộ ảnh
        qr_data, engine = _try_scan(img)
        
        # 2. Quét góc phần tư phía trên bên phải (CCCD) nếu toàn bộ ảnh thất bại
        if not qr_data:
            h, w = img.shape[:2]
            crop = img[0:int(h/2), int(w/2):w]
            qr_data, engine = _try_scan(crop)

        if qr_data:
            return qr_data, engine, None, img
        else:
            return None, None, "QR không đọc được", img

    except Exception as e:
        return None, None, f"Lỗi xử lý ảnh: {str(e)}", None

def extract_ocr_data(image_path_or_cv2img):
    """
    Hàm xử lý OCR (Trích xuất văn bản từ ảnh) bằng AI Deepdoc_VietOCR.
    Nhận vào đường dẫn ảnh hoặc object ảnh cv2.
    Trả về một tuple: (dictionary chứa dữ liệu trích xuất, chuỗi ghi chú)
    """
    try:
        if isinstance(image_path_or_cv2img, str):
            import cv2
            img_to_ocr = cv2.imread(image_path_or_cv2img)
            if img_to_ocr is None:
                return {"CCCD": "", "CMND": "", "Họ tên": "", "Ngày sinh": "", "Giới tính": "", "Nơi thường trú gốc": "", "Ngày cấp CCCD": "", "OCR Side": ""}, "Không thể đọc file ảnh"
        else:
            img_to_ocr = image_path_or_cv2img
            
        # Trích xuất toàn bộ text từ ảnh
        text = extract_text_from_image(img_to_ocr)
    except Exception as e:
        return {}, f"Lỗi thư viện OCR: {str(e)}"
        
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
    # Bước 2.1: Ưu tiên tìm chuỗi 12 số đứng độc lập bắt đầu bằng số 0 (thường là ở mặt trước thẻ cũ)
    cccd_match = re.search(r'\b(0\d{11})\b', text)
    if cccd_match:
        data['CCCD'] = cccd_match.group(1)
    else:
        # Bước 2.2: Lấy từ mã MRZ ở mặt sau (Mã MRZ là chuỗi ký tự ở đáy mặt sau thẻ)
        # Tại Việt Nam, thẻ CCCD áp dụng chuẩn ICAO chia số CCCD thành 2 đoạn trong mã MRZ:
        # Ví dụ MRZ có chuỗi: VNM0960051566086... 
        # -> Phân tích: 096005156 (9 số cuối của CCCD) + 6 (Mã kiểm tra) + 086 (3 số đầu của CCCD)
        # Sửa lỗi OCR: Chữ 'O' thường bị AI đọc nhầm thay vì số '0' -> replace 'O' bằng '0'
        text_mrz = text_upper.replace('O', '0') 
        mrz_match = re.search(r'VNM(\d{9})\d(\d{3})', text_mrz)
        if mrz_match:
            # Lắp ráp lại thành CCCD hoàn chỉnh (3 số đầu + 9 số cuối)
            data['CCCD'] = mrz_match.group(2) + mrz_match.group(1)
        else:
            # Bước 2.3: Chặn bắt cuối cùng (Fallback), quét tìm chuỗi 12 số liền nhau bắt đầu bằng số 0
            fallback_match = re.search(r'(0\d{11})', text)
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

    return data, "Lấy bằng OCR"

def process_qr_string(qr_string):
    parts = qr_string.split('|')
    data = {
        'CCCD': parts[0] if len(parts) > 0 else '',
        'CMND': parts[1] if len(parts) > 1 else '',
        'Họ tên': parts[2] if len(parts) > 2 else '',
        'Ngày sinh': format_date(parts[3]) if len(parts) > 3 else '',
        'Giới tính': parts[4] if len(parts) > 4 else '',
        'Nơi thường trú gốc': parts[5] if len(parts) > 5 else '',
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

def call_address_api(address_list, max_workers=20):
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
    
    # Cấu hình luồng xử lý
    num_threads_input = Prompt.ask("\n[cyan]Nhập số luồng xử lý ảnh song song[/cyan] (Enter để mặc định là 4)", default="4").strip()
    try:
        num_threads = int(num_threads_input) if num_threads_input else 4
    except ValueError:
        console.print("[yellow]⚠️ Giá trị không hợp lệ, sử dụng mặc định: 4 luồng.[/yellow]")
        num_threads = 4

    api_threads_input = Prompt.ask("[cyan]Nhập số luồng gọi API địa chỉ song song[/cyan] (Enter để mặc định là 20)", default="20").strip()
    try:
        api_threads = int(api_threads_input) if api_threads_input else 20
    except ValueError:
        console.print("[yellow]⚠️ Giá trị không hợp lệ, sử dụng mặc định: 20 luồng.[/yellow]")
        api_threads = 20

    # Wizard confirmation
    confirm = Confirm.ask("\n[bold yellow]Bạn có muốn bắt đầu xử lý ngay bây giờ không?[/bold yellow]")
    if not confirm:
        console.print("[yellow]Đã hủy quá trình.[/yellow]")
        return

    console.print("\n")
    console.print(Panel(f"[bold cyan]🚀 BẮT ĐẦU XỬ LÝ {len(image_paths)} ẢNH VỚI {num_threads} LUỒNG...[/bold cyan]", border_style="green"))

    processed_data = []
    seen_cccds = set()
    
    def process_single_image(img_path):
        qr_string, engine, err, img = extract_qr_data(img_path)
        
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
                ocr_data, ocr_note = extract_ocr_data(img)
                
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
        
        is_qr = bool(item.get('QR Raw'))
        if is_qr:
            if not is_new_record:
                if record['has_ocr_data'] and not record['has_qr_data']:
                    console.print(f"   [yellow]→ [GỘP DỮ LIỆU][/yellow] GHI ĐÈ thông tin từ ảnh {item['Image Path']} (Đọc mã QR) lên thông tin OCR trước đó của CCCD {cccd}")
                elif record['has_qr_data']:
                    console.print(f"   [yellow]→ [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin từ ảnh {item['Image Path']} vì đã quét mã QR thành công trước đó cho CCCD {cccd}")
            
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
            if not is_new_record:
                if record['has_qr_data']:
                    console.print(f"   [yellow]→ [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin trùng lặp từ ảnh {item['Image Path']} (OCR) vì đã có dữ liệu QR chuẩn xác của CCCD {cccd}")
                elif record['has_ocr_data']:
                    console.print(f"   [yellow]→ [GỘP DỮ LIỆU][/yellow] Bỏ qua thông tin trùng lặp từ ảnh {item['Image Path']} (OCR) vì đã xử lý ảnh OCR trước đó cho CCCD {cccd}")
            
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

    print("\n" + "="*40)
    print("✨ CHUẨN BỊ XUẤT FILE EXCEL ✨")
    print("="*40)
    
    exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"ket_qua_{timestamp}.xlsx"
    
    custom_name = input(f"\nNhập tên file Excel muốn lưu (nhấn Enter để dùng tên mặc định '{default_filename}'): ").strip()
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
    for row in processed_data:
        if row.get('Full Image Path Front'): used_images.add(row['Full Image Path Front'])
        if row.get('Full Image Path Back'): used_images.add(row['Full Image Path Back'])
        
    duplicate_files = [item for item in extracted_items if item['Full Image Path'] not in used_images]
    ws_dup = wb.create_sheet(title="duplicate")
    ws_dup.append(["STT", "Tên file"])
    for i, item in enumerate(duplicate_files, 1):
        ws_dup.append([i, item['Image Path']])
    
    wb.save(output_filename)
    
    print("\nĐang tạo các file nén zip...")
    
    import shutil
    
    # 1. original.zip
    original_zip_path = os.path.join(exports_dir, 'original.zip')
    with zipfile.ZipFile(original_zip_path, 'w') as zf:
        for path in image_paths:
            if os.path.exists(path):
                zf.write(path, os.path.basename(path))
    print(f" -> Đã tạo original.zip với {len(image_paths)} file.")
    
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
                
    print(f" -> Đã tạo rename.zip với {count_rename} file đã được đổi tên (trong CC và CCCD).")
    
    # 3. Khôi phục lại các file nén phân loại cũ
    def create_zip_helper(zip_name, file_paths):
        if not file_paths:
            return
        zip_path = os.path.join(exports_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for fpath in file_paths:
                if os.path.exists(fpath):
                    zf.write(fpath, os.path.basename(fpath))
        print(f" -> Đã tạo {zip_name} với {len(file_paths)} file.")

    qr_files = [item['Full Image Path'] for item in extracted_items if item.get('Scan Type') == 'QR_scanned']
    ocr_files = [item['Full Image Path'] for item in extracted_items if item.get('Scan Type') == 'OCR_scanned']
    dup_files = [item['Full Image Path'] for item in duplicate_files]
    
    create_zip_helper('QR_scanned.zip', qr_files)
    create_zip_helper('OCR_scanned.zip', ocr_files)
    create_zip_helper('duplicate.zip', dup_files)
    
    console.print("\n" + "🎉"*15)
    console.print(f"[bold green]ĐÃ HOÀN TẤT THÀNH CÔNG![/bold green]")
    console.print(f"File kết quả được lưu tại: [yellow]{os.path.abspath(output_filename)}[/yellow]")
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
