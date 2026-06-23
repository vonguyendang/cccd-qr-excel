import re
with open("wizard/main.py", "r") as f:
    code = f.read()

def inject_preserve_logic(code):
    # QR Front
    old_qr_front = """            if len(fields) == 7:
                record['Ảnh mặt trước CCCD/CC'] = item['Image Path']
                record['Full Image Path Front'] = item['Full Image Path']"""
    new_qr_front = """            if len(fields) == 7:
                if record['Ảnh mặt trước CCCD/CC']:
                    existing = record.get('Ảnh khác (SMS/Chụp màn hình/...)', '')
                    record['Ảnh khác (SMS/Chụp màn hình/...)'] = f"{existing}, {item['Image Path']}".strip(', ')
                else:
                    record['Ảnh mặt trước CCCD/CC'] = item['Image Path']
                    record['Full Image Path Front'] = item['Full Image Path']"""
    code = code.replace(old_qr_front, new_qr_front)
    
    # QR Back
    old_qr_back = """            elif len(fields) >= 10:
                record['Ảnh mặt sau CCCD/CC'] = item['Image Path']
                record['Full Image Path Back'] = item['Full Image Path']"""
    new_qr_back = """            elif len(fields) >= 10:
                if record['Ảnh mặt sau CCCD/CC']:
                    existing = record.get('Ảnh khác (SMS/Chụp màn hình/...)', '')
                    record['Ảnh khác (SMS/Chụp màn hình/...)'] = f"{existing}, {item['Image Path']}".strip(', ')
                else:
                    record['Ảnh mặt sau CCCD/CC'] = item['Image Path']
                    record['Full Image Path Back'] = item['Full Image Path']"""
    code = code.replace(old_qr_back, new_qr_back)
    
    # OCR Front
    old_ocr_front = """            if item.get('OCR Side') == 'Front':
                record['OCR Image Path Front'] = item['Image Path']
                record['Full OCR Image Path Front'] = item['Full Image Path']"""
    new_ocr_front = """            if item.get('OCR Side') == 'Front':
                if record.get('OCR Image Path Front') or record.get('Ảnh mặt trước CCCD/CC'):
                    existing = record.get('Ảnh khác (SMS/Chụp màn hình/...)', '')
                    record['Ảnh khác (SMS/Chụp màn hình/...)'] = f"{existing}, {item['Image Path']}".strip(', ')
                else:
                    record['OCR Image Path Front'] = item['Image Path']
                    record['Full OCR Image Path Front'] = item['Full Image Path']"""
    code = code.replace(old_ocr_front, new_ocr_front)

    # OCR Back
    old_ocr_back = """            elif item.get('OCR Side') == 'Back':
                record['OCR Image Path Back'] = item['Image Path']
                record['Full OCR Image Path Back'] = item['Full Image Path']"""
    new_ocr_back = """            elif item.get('OCR Side') == 'Back':
                if record.get('OCR Image Path Back') or record.get('Ảnh mặt sau CCCD/CC'):
                    existing = record.get('Ảnh khác (SMS/Chụp màn hình/...)', '')
                    record['Ảnh khác (SMS/Chụp màn hình/...)'] = f"{existing}, {item['Image Path']}".strip(', ')
                else:
                    record['OCR Image Path Back'] = item['Image Path']
                    record['Full OCR Image Path Back'] = item['Full Image Path']"""
    code = code.replace(old_ocr_back, new_ocr_back)

    # OCR Unknown
    old_ocr_unk = """            else:
                record['OCR Image Path Unknown'] = item['Image Path']
                record['Full OCR Image Path Unknown'] = item['Full Image Path']"""
    new_ocr_unk = """            else:
                if record.get('OCR Image Path Unknown'):
                    existing = record.get('Ảnh khác (SMS/Chụp màn hình/...)', '')
                    record['Ảnh khác (SMS/Chụp màn hình/...)'] = f"{existing}, {item['Image Path']}".strip(', ')
                else:
                    record['OCR Image Path Unknown'] = item['Image Path']
                    record['Full OCR Image Path Unknown'] = item['Full Image Path']"""
    code = code.replace(old_ocr_unk, new_ocr_unk)
    
    return code

new_code = inject_preserve_logic(code)
with open("wizard/main.py", "w") as f:
    f.write(new_code)
print("Done")
