import os
import glob
import pandas as pd
import unicodedata
import openpyxl
from openpyxl.styles import PatternFill

def remove_accents(input_str):
    if pd.isna(input_str) or input_str is None:
        return ""
    s = str(input_str).strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd')
    return s

def main():
    exports_dir = 'exports'
    target_file = '/Users/dangvo/DATA/THAOPHAM/bvnhidongtpct.xlsx'
    
    print("Bắt đầu xử lý...")
    
    # 1. Đọc và gộp dữ liệu từ thư mục exports
    export_files = glob.glob(os.path.join(exports_dir, '*.xlsx'))
    if not export_files:
        print(f"Không tìm thấy file excel nào trong thư mục '{exports_dir}'")
        return
    
    exports_df_list = []
    for f in export_files:
        try:
            df = pd.read_excel(f)
            exports_df_list.append(df)
            print(f" - Đã đọc file: {f}")
        except Exception as e:
            print(f"Lỗi đọc file {f}: {e}")
            
    if not exports_df_list:
        return
        
    exports_df = pd.concat(exports_df_list, ignore_index=True)
    
    if 'Họ tên' not in exports_df.columns or 'Ghi chú' not in exports_df.columns:
        print("Lỗi: Các file trong exports cần có cột 'Họ tên' và 'Ghi chú'")
        return
        
    # Tạo mapping name -> data
    name_to_data = {}
    for _, row in exports_df.iterrows():
        name_val = row['Họ tên']
        note_val = row.get('Ghi chú')
        cccd_val = row.get('CCCD')
        cmnd_val = row.get('CMND')
        
        name = remove_accents(name_val)
        note = str(note_val).strip() if pd.notna(note_val) else ""
        note_unaccented = remove_accents(note)
        cccd = str(cccd_val).strip() if pd.notna(cccd_val) else ""
        cmnd = str(cmnd_val).strip() if pd.notna(cmnd_val) else ""
        
        if not name:
            continue
            
        current_data = name_to_data.get(name, {})
        current_status = current_data.get("status")
        
        new_status = current_status
        # Ưu tiên "Đọc mã QR" nếu có nhiều kết quả trùng tên
        if "doc ma qr" in note_unaccented:
            new_status = "Đọc mã QR"
        elif "qr khong doc duoc" in note_unaccented:
            if current_status != "Đọc mã QR":
                new_status = "QR không đọc được"
        else:
            # Nếu có tên trong file export nhưng không có 2 ghi chú trên, vẫn đánh dấu là Chưa đầy đủ
            if not current_status:
                new_status = "QR không đọc được"
                
        # Cập nhật CCCD, CMND (Ưu tiên lấy nếu chưa có, hoặc nếu mới chuyển lên trạng thái "Đọc mã QR")
        new_cccd = current_data.get("cccd", "")
        if cccd and cccd.lower() not in ['nan', 'none']:
            if not new_cccd or new_status == "Đọc mã QR":
                new_cccd = cccd
                
        new_cmnd = current_data.get("cmnd", "")
        if cmnd and cmnd.lower() not in ['nan', 'none']:
            if not new_cmnd or new_status == "Đọc mã QR":
                new_cmnd = cmnd
                
        name_to_data[name] = {
            "status": new_status,
            "cccd": new_cccd,
            "cmnd": new_cmnd
        }
                
    print(f"Đã tải thông tin {len(name_to_data)} người duy nhất từ thư mục exports.")
    
    # 2. Xử lý file đích bằng openpyxl để giữ nguyên định dạng
    if not os.path.exists(target_file):
        print(f"Lỗi: Không tìm thấy file đích '{target_file}'")
        return
        
    try:
        print(f"Đang đọc file đích: {target_file}")
        wb = openpyxl.load_workbook(target_file)
        ws = wb.active
    except Exception as e:
        print(f"Lỗi khi đọc file '{target_file}': {e}")
        return
        
    # Tìm dòng chứa tiêu đề
    header_row = None
    headers = {}
    for r in range(1, min(20, ws.max_row + 1)):
        headers = {str(cell.value).strip(): idx for idx, cell in enumerate(ws[r], start=1) if cell.value}
        if 'HỌ VÀ TÊN' in headers:
            header_row = r
            break
            
    if not header_row:
        print("Lỗi: Không tìm thấy dòng tiêu đề có chứa 'HỌ VÀ TÊN' trong 20 dòng đầu")
        return
    
    col_name = headers.get('HỌ VÀ TÊN')
    col_name_no_accent = headers.get('HỌ VÀ TÊN KHÔNG DẤU')
    col_cccd = headers.get('CCCD')
    col_cmnd = headers.get('CMND')
    
    col_full = headers.get('ĐÃ CÓ THÔNG TIN CCCD (Đầy đủ)')
    col_partial = headers.get('ĐÃ CÓ THÔNG TIN CCCD (Chưa đầy đủ)')
    col_none = headers.get('CHƯA CÓ THÔNG TIN CCCD')
    
    if not col_name:
        print("Lỗi: File đích không có cột 'HỌ VÀ TÊN'")
        return
    if not (col_full and col_partial and col_none):
        print("Lỗi: File đích thiếu các cột đánh dấu (Đầy đủ, Chưa đầy đủ, CHƯA CÓ THÔNG TIN CCCD)")
        return
        
    # Duyệt qua các dòng và đánh dấu
    count_full = 0
    count_partial = 0
    count_none = 0
    
    # Khởi tạo các màu
    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    pink_fill = PatternFill(start_color="FFC0CB", end_color="FFC0CB", fill_type="solid")
    no_fill = PatternFill(fill_type=None)
    
    print("Đang đối chiếu dữ liệu...")
    for row in range(header_row + 1, ws.max_row + 1):
        # Xóa đánh dấu cũ (nếu có)
        ws.cell(row=row, column=col_full).value = None
        ws.cell(row=row, column=col_partial).value = None
        ws.cell(row=row, column=col_none).value = None
        
        target_name_cell = ws.cell(row=row, column=col_name).value
        if not target_name_cell:
            continue
            
        unaccented_target = remove_accents(target_name_cell)
        
        # Bổ sung Họ tên không dấu (In hoa)
        if col_name_no_accent:
            ws.cell(row=row, column=col_name_no_accent).value = unaccented_target.upper()
            
        data = name_to_data.get(unaccented_target, {})
        status = data.get("status")
        
        # Bổ sung CCCD, CMND nếu tìm thấy
        if col_cccd and data.get("cccd"):
            ws.cell(row=row, column=col_cccd).value = data.get("cccd")
        if col_cmnd and data.get("cmnd"):
            ws.cell(row=row, column=col_cmnd).value = data.get("cmnd")
        
        if status == "Đọc mã QR":
            ws.cell(row=row, column=col_full).value = 'X'
            count_full += 1
            # Xóa màu của dòng
            for col_idx in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col_idx).fill = no_fill
        elif status == "QR không đọc được":
            ws.cell(row=row, column=col_partial).value = 'X'
            count_partial += 1
            # Tô màu vàng cho dòng
            for col_idx in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col_idx).fill = yellow_fill
        else:
            ws.cell(row=row, column=col_none).value = 'X'
            count_none += 1
            # Tô màu hồng cho dòng
            for col_idx in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col_idx).fill = pink_fill
            
    # 3. Lưu file
    try:
        print("Đang lưu file đích...")
        wb.save(target_file)
        print(f"Hoàn thành! Đã lưu kết quả vào '{target_file}'.")
        print(f"\n--- THỐNG KÊ ---")
        print(f"Tổng số dòng đã xử lý: {count_full + count_partial + count_none}")
        print(f" - Đã có CCCD (Đầy đủ): {count_full}")
        print(f" - Đã có CCCD (Chưa đầy đủ): {count_partial}")
        print(f" - Chưa có thông tin: {count_none}")
    except Exception as e:
        print(f"Lỗi khi lưu file '{target_file}'. Vui lòng đảm bảo file không bị mở ở chương trình khác. Lỗi: {e}")

if __name__ == "__main__":
    main()
