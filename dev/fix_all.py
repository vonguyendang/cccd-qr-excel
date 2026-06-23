import re
with open("wizard/main.py", "r") as f:
    code = f.read()

# 1. Add is_sms logic
code = code.replace("                # Phân tích trật tự từ trên xuống dưới để phạt ảnh bị lộn ngược (180 độ)", 
                    '                is_sms = any(kw in upper_text for kw in ["THUÊ BAO","TTTB","THUE BAO","TB", "MOBIFONE", "VINAPHONE", "VIETTEL", "TRẢ TRƯỚC", "TRA TRUOC", "TÀI KHOẢN", "TAI KHOAN", "GÓI CƯỚC", "GOI CUOC", "MẬT KHẨU", "QUÝ KHÁCH"])\n                \n                # Phân tích trật tự từ trên xuống dưới để phạt ảnh bị lộn ngược (180 độ)')

code = code.replace("                    # Phân tích trật tự từ trên xuống dưới để phạt ảnh bị lộn ngược (180 độ)", 
                    '                    is_sms = any(kw in upper_text for kw in ["THUÊ BAO","TTTB","THUE BAO","TB", "MOBIFONE", "VINAPHONE", "VIETTEL", "TRẢ TRƯỚC", "TRA TRUOC", "TÀI KHOẢN", "TAI KHOAN", "GÓI CƯỚC", "GOI CUOC", "MẬT KHẨU", "QUÝ KHÁCH"])\n                    \n                    # Phân tích trật tự từ trên xuống dưới để phạt ảnh bị lộn ngược (180 độ)')

code = code.replace("best_front_note = f\"Lấy bằng OCR ({rot_name})\"", 
                    "best_front_note = f\"Lấy bằng OCR ({rot_name})\" + (\" [SMS]\" if is_sms else \"\")")

code = code.replace("best_front_note = f\"Lấy bằng OCR toàn phần ({rot_name})\"", 
                    "best_front_note = f\"Lấy bằng OCR toàn phần ({rot_name})\" + (\" [SMS]\" if is_sms else \"\")")

code = code.replace("                if best_front_score >= 250 or (data_rot.get('CCCD') and data_rot.get('Họ tên') and data_rot.get('Ngày sinh')):\n                    break", 
                    "                if best_front_score >= 250 or (data_rot.get('CCCD') and data_rot.get('Họ tên') and data_rot.get('Ngày sinh')) or is_sms:\n                    break")

code = code.replace("                    if best_front_score >= 250 or (data_rot.get('CCCD') and data_rot.get('Họ tên') and data_rot.get('Ngày sinh')):\n                        break", 
                    "                    if best_front_score >= 250 or (data_rot.get('CCCD') and data_rot.get('Họ tên') and data_rot.get('Ngày sinh')) or is_sms:\n                        break")

code = code.replace("            if missing_critical(best_data) and best_img is not None:\n                clahe =", 
                    "            is_sms_detected = \"[SMS]\" in best_note\n            if missing_critical(best_data) and best_img is not None and not is_sms_detected:\n                clahe =")

# 2. Add ADDNN1 fix
if "text_upper = re.sub(r'\\bADDNN1'" not in code:
    code = code.replace("text_upper = text.upper()\n\n                # ---------------------------------------------------------", 
                        "text_upper = text.upper()\n                # Sửa lỗi kinh điển OCR trên CCCD: IDVNM0 bị đọc thành ADDNN1, I0VNM, 1DVNM\n                text_upper = re.sub(r'\\bADDNN1', 'IDVNM0', text_upper)\n                text_upper = re.sub(r'\\b[I1L]D?VNM[O0]?', 'IDVNM0', text_upper)\n\n                # ---------------------------------------------------------")

# 3. Use text_upper for MRZ in parse_ocr_text
if "text_mrz_search = text_upper.replace('K', '<')" not in code:
    old_mrz = "                # Khôi phục một phần dấu < bị nhận diện sai thành K hoặc khoảng trắng (CHỈ cho mrz_lines xuất ra)\n                text_bottom_fixed = text_bottom.replace('K', '<').replace(' ', '<')\n                clean_mrz_text = re.sub(r'[^A-Z0-9<\\n]', '', text_bottom_fixed)"
    new_mrz = "                # Tìm MRZ trên TOÀN BỘ text (tránh việc crop sai dòng)\n                text_mrz_search = text_upper.replace('K', '<').replace(' ', '<')\n                clean_mrz_text = re.sub(r'[^A-Z0-9<\\n]', '', text_mrz_search)"
    code = code.replace(old_mrz, new_mrz)

with open("wizard/main.py", "w") as f:
    f.write(code)
print("Done")
