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
import pytesseract
import re
import concurrent.futures


def format_date(date_str):
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[0:2]}/{date_str[2:4]}/{date_str[4:8]}"

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
            return None, "Lỗi đọc file ảnh", None

        # Try decoding directly
        decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE])
        
        # If not found, try grayscale and thresholding for blurry/dark images
        if not decoded_objects:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            decoded_objects = decode(gray, symbols=[ZBarSymbol.QRCODE])
            
            if not decoded_objects:
                # Apply adaptive thresholding
                thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                decoded_objects = decode(thresh, symbols=[ZBarSymbol.QRCODE])

        if not decoded_objects:
            # Fallback to WeChat QRCode CNN detector
            model_paths = [
                'models/detect.prototxt', 'models/detect.caffemodel',
                'models/sr.prototxt', 'models/sr.caffemodel'
            ]
            if all(os.path.exists(p) for p in model_paths):
                try:
                    detector = cv2.wechat_qrcode_WeChatQRCode(*model_paths)
                    res, _ = detector.detectAndDecode(img)
                    if res and len(res) > 0:
                        return res[0], None, img
                except Exception as e:
                    pass
            return None, "QR không đọc được", img

        # Assuming we just need the first QR code found
        qr_data = decoded_objects[0].data.decode('utf-8')
        return qr_data, None, img

    except Exception as e:
        return None, f"Lỗi xử lý ảnh: {str(e)}", None

def extract_ocr_data(img):
    try:
        text = pytesseract.image_to_string(img, lang='vie')
    except Exception as e:
        return {}, f"Lỗi thư viện OCR: {str(e)}"
        
    data = {
        'CCCD': '', 'CMND': '', 'Họ tên': '', 'Ngày sinh': '',
        'Giới tính': '', 'Nơi thường trú gốc': '', 'Ngày cấp CCCD': ''
    }
    
    # Extract CCCD: 12 digits
    cccd_match = re.search(r'\b\d{12}\b', text)
    if cccd_match:
        data['CCCD'] = cccd_match.group(0)
        
    all_dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)
        
    # Extract Gender
    if re.search(r'\bNam\b', text, re.IGNORECASE):
        data['Giới tính'] = 'Nam'
    elif re.search(r'\bN[uưứữ][\s]*\b', text, re.IGNORECASE) or re.search(r'\bNữ\b', text, re.IGNORECASE):
        data['Giới tính'] = 'Nữ'
        
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
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
                    
        # 3. Address
        if "nơi thường trú" in line_lower or "nơi cư trú" in line_lower or "residence" in line_lower:
            addr_parts = []
            if ":" in line:
                addr_parts.append(line.split(":", 1)[1].strip())
            if i + 1 < len(lines) and "giá trị đến" not in lines[i+1].lower() and "expiry" not in lines[i+1].lower():
                addr_parts.append(lines[i+1].replace('|', '').strip())
            if i + 2 < len(lines) and "giá trị đến" not in lines[i+2].lower() and "expiry" not in lines[i+2].lower():
                next2 = lines[i+2].replace('|', '').strip()
                if len(next2) > 5 and not re.search(r'\d{2}/\d{2}/\d{4}', next2):
                    addr_parts.append(next2)
            addr = ", ".join(filter(bool, addr_parts))
            data['Nơi thường trú gốc'] = re.sub(r',\s*,', ',', addr).lstrip(', ')
            
        # 4. Issue Date (Back of card)
        if "ngày, tháng, năm" in line_lower or "date, month, year" in line_lower or "date of issue" in line_lower:
            for j in range(i, min(i+3, len(lines))):
                m = re.search(r'\b\d{2}/\d{2}/\d{4}\b', lines[j])
                if m:
                    data['Ngày cấp CCCD'] = m.group(0)
                    break

    # Fallback DOB
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
        response = requests.post(
            'https://tienich.vnhub.com/api/wards', 
            json={"address": addr},
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
        else:
            err_msg = "Không tìm thấy địa chỉ tương ứng"
            if res_data.get('success') is False and res_data.get('error'):
                err_msg = f"API bị lỗi: {res_data.get('error')}"
            return {
                "original": addr,
                "success": False,
                "error": err_msg
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

def main():
    print("="*60)
    print("   PHẦN MỀM TRÍCH XUẤT MÃ QR TỪ ẢNH CCCD RA EXCEL   ")
    print("="*60)
    
    input_dir = ""
    if len(sys.argv) >= 2:
        input_dir = sys.argv[1]
    else:
        print("\n[Hướng dẫn]: Kéo thả thư mục chứa ảnh vào cửa sổ này,")
        print("hoặc copy đường dẫn thư mục và dán vào đây.")
        input_dir = input("\nNhập đường dẫn thư mục chứa ảnh CCCD: ").strip()

    # Xóa dấu nháy đơn/kép nếu người dùng kéo thả thư mục vào terminal có sinh ra
    input_dir = input_dir.strip('\'"')

    if not input_dir or not os.path.isdir(input_dir):
        print(f"\n❌ Lỗi: Thư mục '{input_dir}' không tồn tại hoặc đường dẫn không đúng.")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

    # Search for common image formats
    image_paths = []
    for ext in ('*.jpg', '*.jpeg', '*.png', '*.heic', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.HEIC', '*.WEBP'):
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

    if not image_paths:
        print("\n❌ Thật tiếc, không tìm thấy file ảnh nào (.jpg, .png) trong thư mục này.")
        input("Nhấn Enter để thoát...")
        sys.exit(0)

    print(f"\n✅ Đã quét thư mục và tìm thấy tổng cộng {len(image_paths)} file ảnh.")
    
    # Cấu hình luồng xử lý
    num_threads_input = input("\nNhập số luồng xử lý ảnh song song (Enter để mặc định là 4): ").strip()
    try:
        num_threads = int(num_threads_input) if num_threads_input else 4
    except ValueError:
        print("⚠️ Giá trị không hợp lệ, sử dụng mặc định: 4 luồng.")
        num_threads = 4

    api_threads_input = input("Nhập số luồng gọi API địa chỉ song song (Enter để mặc định là 20): ").strip()
    try:
        api_threads = int(api_threads_input) if api_threads_input else 20
    except ValueError:
        print("⚠️ Giá trị không hợp lệ, sử dụng mặc định: 20 luồng.")
        api_threads = 20

    # Wizard confirmation
    while True:
        confirm = input("\nBạn có muốn bắt đầu xử lý ngay bây giờ không? (y/n): ").strip().lower()
        if confirm == 'y' or confirm == '':
            break
        elif confirm == 'n':
            print("Đã hủy quá trình.")
            sys.exit(0)
        else:
            print("Vui lòng nhập 'y' (có) hoặc 'n' (không).")

    print("\n" + "-"*40)
    print(f"🚀 BẮT ĐẦU XỬ LÝ {len(image_paths)} ẢNH VỚI {num_threads} LUỒNG...")
    print("-" * 40)

    processed_data = []
    seen_cccds = set()
    
    def process_single_image(img_path, idx, total):
        print(f"[{idx+1}/{total}] Đang đọc {os.path.basename(img_path)}...")
        qr_string, err, img = extract_qr_data(img_path)
        
        row_data = {
            'Họ tên': '', 'CCCD': '', 'CMND': '', 'Giới tính': '',
            'Ngày sinh': '', 'Nơi thường trú gốc': '', 'Địa chỉ chuẩn hóa mới': '',
            'Ngày cấp CCCD': '', 'Ghi chú': '', 'QR Raw': ''
        }
        notes = []

        if qr_string:
            row_data['QR Raw'] = qr_string
            extracted, validation_notes = process_qr_string(qr_string)
            row_data.update(extracted)
            notes.extend(validation_notes)
        else:
            if err:
                notes.append(err)
            
            # Fallback to OCR
            if img is not None:
                print(f"   -> [{os.path.basename(img_path)}] Không đọc được QR, đang thử quét OCR...")
                ocr_data, ocr_note = extract_ocr_data(img)
                row_data.update(ocr_data)
                notes.append(ocr_note)
                
        row_data['Ghi chú'] = '; '.join(notes)
        return row_data

    # Chạy song song với ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_img = {executor.submit(process_single_image, path, idx, len(image_paths)): path for idx, path in enumerate(image_paths)}
        
        for future in concurrent.futures.as_completed(future_to_img):
            img_path = future_to_img[future]
            try:
                row_data = future.result()
                
                # Deduplication thông minh (Giống Server)
                cccd_num = row_data['CCCD']
                if cccd_num:
                    if cccd_num in seen_cccds:
                        is_qr = bool(row_data.get('QR Raw'))
                        existing_idx = next((i for i, v in enumerate(processed_data) if v.get('CCCD') == cccd_num), None)
                        
                        if existing_idx is not None:
                            existing_is_qr = bool(processed_data[existing_idx].get('QR Raw'))
                            
                            def count_info(d):
                                keys = ['Họ tên', 'CMND', 'Giới tính', 'Ngày sinh', 'Nơi thường trú gốc', 'Ngày cấp CCCD']
                                return sum(1 for k in keys if d.get(k))

                            if not existing_is_qr and is_qr:
                                print(f"   -> 🔄 Cập nhật CCCD {cccd_num}: Ghi đè bản OCR cũ bằng bản quét QR chính xác hơn.")
                                processed_data[existing_idx] = row_data
                            else:
                                old_count = count_info(processed_data[existing_idx])
                                new_count = count_info(row_data)
                                if new_count > old_count:
                                    print(f"   -> 🔄 Cập nhật CCCD {cccd_num}: Ghi đè bằng bản quét mới có nhiều thông tin hơn ({new_count} > {old_count}).")
                                    processed_data[existing_idx] = row_data
                                else:
                                    print(f"   -> ⚠️ Bỏ qua vì đã xử lý CCCD {cccd_num} trước đó (Trùng lặp).")
                        continue
                    else:
                        seen_cccds.add(cccd_num)
                    
                processed_data.append(row_data)
            except Exception as exc:
                print(f"❌ Lỗi khi xử lý ảnh {os.path.basename(img_path)}: {exc}")
    # Lấy danh sách địa chỉ duy nhất
    print("Đang chuẩn bị gửi dữ liệu lên API...")
    unique_addresses = list(set([item['Nơi thường trú gốc'] for item in processed_data if item.get('Nơi thường trú gốc')]))
    address_map = {}

    # Gọi API chuẩn hóa địa chỉ theo batch
    if unique_addresses:
        print(f"Đang gọi API chuẩn hóa cho {len(unique_addresses)} địa chỉ duy nhất (với {api_threads} luồng)...")
        batch_size = 100
        for i in range(0, len(unique_addresses), batch_size):
            batch = unique_addresses[i:i+batch_size]
            api_results = call_address_api(batch, max_workers=api_threads)
            
            for j, result in enumerate(api_results):
                if j < len(batch):
                    address_map[batch[j]] = result

    # Cập nhật kết quả API vào dữ liệu
    for row in processed_data:
        addr = row.get('Nơi thường trú gốc')
        if addr and addr in address_map:
            result = address_map[addr]
            new_notes = []
            if row['Ghi chú']:
                new_notes.append(row['Ghi chú'])
            
            if result.get('success'):
                row['Địa chỉ chuẩn hóa mới'] = result.get('converted', '')
                if result.get('notSure'):
                    new_notes.append("Địa chỉ chuyển đổi chưa chắc chắn")
            else:
                err_msg = result.get('error', 'Lỗi không xác định khi chuẩn hóa')
                new_notes.append(err_msg)
            
            row['Ghi chú'] = '; '.join(new_notes)

    # Export to Excel
    print("Đang xuất file Excel...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    headers = [
        "STT", "Họ tên", "CCCD", "CMND", "Giới tính", "Ngày sinh", 
        "Nơi thường trú gốc", "Địa chỉ chuẩn hóa mới", "Ngày cấp CCCD", "Ghi chú"
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
            row_data['Ghi chú']
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

    wb.save(output_filename)
    
    print("\n" + "🎉"*15)
    print(f"ĐÃ HOÀN TẤT THÀNH CÔNG!")
    print(f"File kết quả được lưu tại: {os.path.abspath(output_filename)}")
    print("🎉"*15 + "\n")
    
    input("Nhấn Enter để thoát chương trình...")

if __name__ == '__main__':
    main()
