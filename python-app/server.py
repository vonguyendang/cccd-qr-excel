import os
import sys
import json
import base64
import uuid
import datetime
import asyncio
import httpx
from io import BytesIO
import numpy as np

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

import cv2
import openpyxl
from openpyxl.styles import Font

app = FastAPI(title="CCCD QR API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variables
detector = None

@app.on_event("startup")
async def load_models():
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
            print("Loaded WeChat QRCode detector.")
        except Exception as e:
            print(f"Error loading detector: {e}")
    else:
        print("Model files not found.")

class ScanQRRequest(BaseModel):
    imageBase64: str
    filename: Optional[str] = None

@app.post("/api/scan_qr")
async def scan_qr(req: ScanQRRequest):
    fname = f"'{req.filename}'" if req.filename else "từ Live Camera"
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Nhận yêu cầu quét ảnh {fname}...", flush=True)
    if not detector:
        print("-> Lỗi: Mô hình WeChat QRCode chưa được tải.", flush=True)
        return {"success": False, "error": "Model not loaded"}
    
    # decode base64
    base64_str = req.imageBase64
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    
    try:
        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("-> Lỗi: Dữ liệu ảnh không hợp lệ.", flush=True)
            return {"success": False, "error": "Invalid image"}
            
        res, _ = detector.detectAndDecode(img)
        if res and len(res) > 0:
            print(f"-> Quét thành công QR: {res[0][:50]}...", flush=True)
            return {"success": True, "data": res[0]}
            
        print("-> Không tìm thấy mã QR trong ảnh.", flush=True)
        return {"success": False, "error": "QR not found"}
    except Exception as e:
        print(f"-> Lỗi hệ thống khi quét ảnh: {str(e)}", flush=True)
        return {"success": False, "error": str(e)}

def format_date(date_str):
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[0:2]}/{date_str[2:4]}/{date_str[4:8]}"

def process_qr_string(qr_str):
    parts = qr_str.split('|')
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

async def fetch_single_address_async(client, addr):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) Gecko/20100101 Firefox/151.0',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'x-kas': '89232422',
        'Origin': 'https://tienich.vnhub.com',
        'Referer': 'https://tienich.vnhub.com/'
    }
    try:
        response = await client.post(
            'https://tienich.vnhub.com/api/wards',
            json={"address": addr},
            headers=headers,
            timeout=15.0
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

class ExportItem(BaseModel):
    filename: Optional[str] = None
    qrData: Optional[str] = None
    error: Optional[str] = None
    fromOCR: Optional[bool] = False
    ocrData: Optional[Dict[str, str]] = None

class ExportRequest(BaseModel):
    data: List[ExportItem]

@app.post("/api/export")
async def export_excel(req: ExportRequest):
    items = req.data
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Nhận yêu cầu xuất Excel cho {len(items)} bản ghi.", flush=True)
    processed_data = []
    seen_cccds = set()
    
    for item in items:
        row = {
            'Họ tên': '', 'CCCD': '', 'CMND': '', 'Giới tính': '',
            'Ngày sinh': '', 'Nơi thường trú gốc': '', 'Địa chỉ chuẩn hóa mới': '',
            'Ngày cấp CCCD': '', 'Ghi chú': '', 'QR Raw': ''
        }
        notes = []
        
        if item.error:
            notes.append(item.error)
        elif item.qrData:
            row['QR Raw'] = item.qrData
            extracted, v_notes = process_qr_string(item.qrData)
            
            cccd_num = extracted.get('CCCD', '')
            if cccd_num:
                if cccd_num in seen_cccds:
                    continue
                seen_cccds.add(cccd_num)
                
            row.update(extracted)
            notes.extend(v_notes)
        elif item.fromOCR and item.ocrData:
            extracted = item.ocrData
            notes.append("Lấy bằng OCR")
            
            cccd_num = extracted.get('CCCD', '')
            if cccd_num:
                if cccd_num in seen_cccds:
                    continue
                seen_cccds.add(cccd_num)
                
            row.update(extracted)
            
        row['Ghi chú'] = '; '.join(notes)
        processed_data.append(row)
        
    unique_addresses = list(set([row['Nơi thường trú gốc'] for row in processed_data if row.get('Nơi thường trú gốc')]))
    print(f"-> Phát hiện {len(unique_addresses)} địa chỉ độc nhất cần chuẩn hóa qua VNHub.", flush=True)
    
    # Run async API calls
    address_map = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_address_async(client, addr) for addr in unique_addresses]
        results = await asyncio.gather(*tasks)
        for res in results:
            address_map[res['original']] = res
            if res['success']:
                print(f"  + Thành công: '{res['original']}' -> '{res['converted']}'", flush=True)
            else:
                print(f"  + Thất bại ({res['original']}): {res.get('error')}", flush=True)
            
    # Map back
    for row in processed_data:
        addr = row['Nơi thường trú gốc']
        if addr and addr in address_map:
            result = address_map[addr]
            notes = [row['Ghi chú']] if row['Ghi chú'] else []
            
            if result['success']:
                row['Địa chỉ chuẩn hóa mới'] = result.get('converted', '')
            else:
                notes.append(result.get('error', 'Lỗi không xác định'))
                
            row['Ghi chú'] = '; '.join(notes)
            
    print(f"-> Hoàn tất xử lý dữ liệu. Đang đóng gói file Excel...", flush=True)
    
    # Generate Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    
    headers = [
        "STT", "Họ tên", "CCCD", "CMND", "Giới tính", "Ngày sinh", 
        "Nơi thường trú gốc", "Địa chỉ chuẩn hóa mới", "Ngày cấp CCCD", "Ghi chú", "QR Raw"
    ]
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)
        
    for row_idx, data in enumerate(processed_data, 2):
        ws.cell(row=row_idx, column=1, value=row_idx-1)
        ws.cell(row=row_idx, column=2, value=data.get('Họ tên', ''))
        # Using string to keep leading zeros
        c_cell = ws.cell(row=row_idx, column=3, value=data.get('CCCD', ''))
        c_cell.number_format = '@'
        cm_cell = ws.cell(row=row_idx, column=4, value=data.get('CMND', ''))
        cm_cell.number_format = '@'
        
        ws.cell(row=row_idx, column=5, value=data.get('Giới tính', ''))
        ws.cell(row=row_idx, column=6, value=data.get('Ngày sinh', ''))
        ws.cell(row=row_idx, column=7, value=data.get('Nơi thường trú gốc', ''))
        ws.cell(row=row_idx, column=8, value=data.get('Địa chỉ chuẩn hóa mới', ''))
        ws.cell(row=row_idx, column=9, value=data.get('Ngày cấp CCCD', ''))
        ws.cell(row=row_idx, column=10, value=data.get('Ghi chú', ''))
        ws.cell(row=row_idx, column=11, value=data.get('QR Raw', ''))
        
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width
        
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    # Return Excel file
    headers = {
        'Content-Disposition': 'attachment; filename="ket_qua.xlsx"',
        'Access-Control-Expose-Headers': 'Content-Disposition'
    }
    return StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

# Mount web-app directory as root static files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_app_dir = os.path.join(base_dir, 'web-app')
app.mount("/", StaticFiles(directory=web_app_dir, html=True), name="static")
