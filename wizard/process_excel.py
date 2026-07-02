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
        
    # Tạo mapping name -> status
    name_to_status = {}
    for _, row in exports_df.iterrows():
        name_val = row['Họ tên']
        note_val = row['Ghi chú']
        
        name = remove_accents(name_val)
        note = str(note_val).strip() if pd.notna(note_val) else ""
        note_unaccented = remove_accents(note)
        
        if not name:
            continue
            
        current_status = name_to_status.get(name)
        # Ưu tiên "Đọc mã QR" nếu có nhiều kết quả trùng tên
        if note_unaccented == "doc ma qr":
            name_to_status[name] = "Đọc mã QR"
        elif note_unaccented == "qr khong doc duoc":
            if current_status != "Đọc mã QR":
                name_to_status[name] = "QR không đọc được"
                
    print(f"Đã tải thông tin {len(name_to_status)} người duy nhất từ thư mục exports.")
    
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
        status = name_to_status.get(unaccented_target)
        
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
