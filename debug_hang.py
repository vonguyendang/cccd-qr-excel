import sys, os, time
import concurrent.futures
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')

from wizard.main import IN_COLAB, extract_qr_data, process_qr_string, extract_ocr_data, get_place_of_issue, calculate_expiry_date

def process_single_image(img_path):
    print(f"⏳ Bắt đầu đưa vào AI: {os.path.basename(img_path)}...")
    t0 = time.time()
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
        img = qr_rotated_img
    notes = []

    if qr_string:
        pass
    else:
        if err:
            notes.append(err)
        if img is not None:
            log_msgs.append(f"[yellow]⚠️ Không đọc được QR, đang thử quét OCR...[/yellow]")
            ocr_data, ocr_note, rotated_img = extract_ocr_data(img)
            return ocr_data

    return row_data

img_path = '/Users/dangvo/DATA/THAOPHAM/CCCD_total3days/696.jpg'
print("Starting ThreadPoolExecutor...")
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
future = executor.submit(process_single_image, img_path)
print("Waiting for result...")
try:
    res = future.result(timeout=600)
    print("FINISHED:", res)
except Exception as e:
    print("EXCEPTION:", e)
