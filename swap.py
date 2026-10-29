import re

with open('/Users/dangvo/Projects/cccd-qr-excel/wizard/main.py', 'r') as f:
    content = f.read()

replacement = """
    # -------------------------------------------------------
    # PRIMARY: Geovina.io.vn
    # -------------------------------------------------------
    import os as _os
    last_exception = None
    geovina_failed = False
    
    while True:
        geovina_token = _os.environ.get(
            'GEOVINA_DEMO_TOKEN',
            '1782095814853.ab6fc10225b874be936bd6fe9a020c6e0a5418e03a1215c0463d5628c91083e7'
        )
        geovina_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,vi;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
            'X-Demo-Token': geovina_token,
            'X-Api-Key': 'gvn_5740dceda5cb2424b787f1153da3802a721ae3f6',
            'Referer': 'https://www.geovina.io.vn/',
            'Origin': 'https://www.geovina.io.vn',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=0',
            'TE': 'trailers'
        }
        
        try:
            # Retry nội bộ cho Geovina (tránh 429 Too Many Requests)
            for geo_attempt in range(4):
                geo_resp = _address_session.post(
                    'https://www.geovina.io.vn/parse',
                    data=payload,
                    headers=geovina_headers,
                    timeout=15
                )
                if geo_resp.status_code == 429:
                    time.sleep(2)
                    continue
                if geo_resp.status_code not in (401, 402, 403):
                    geo_resp.raise_for_status()
                break
                
            try:
                geo_data = geo_resp.json()
            except Exception:
                geo_data = {}
            
            is_token_error = False
            if geo_resp.status_code in (401, 402, 403):
                is_token_error = True
            elif not geo_data.get('success'):
                err_text = str(geo_data.get('error', '')).lower()
                if "token" in err_text or "hết hạn" in err_text or "không hợp lệ" in err_text or "unauthorized" in err_text:
                    is_token_error = True
                    
            if is_token_error:
                updated = check_and_prompt_geovina_token(current_failed_token=geovina_token)
                if updated:
                    continue # Thử lại với token mới
                else:
                    last_exception = "Token Geovina đã hết hạn và người dùng đã bỏ qua."
                    geovina_failed = True
                    break

            full_new = geo_data.get('data', {}).get('full_new_address', '')
            if geo_data.get('success') and full_new:
                converted_addr = re.sub(r'\\s+', ' ', full_new).strip(', ')
                return {"original": addr, "success": True, "converted": converted_addr, "source": "geovina", "_processing_time": time.time() - t0}

            last_exception = geo_data.get('error', "Không tìm thấy địa chỉ tương ứng trên Geovina")
            geovina_failed = True
            break

        except Exception as geo_err:
            last_exception = str(geo_err)
            geovina_failed = True
            break

    # -------------------------------------------------------
    # BACKUP: VNHub
    # -------------------------------------------------------
    vnhub_exception = None
    for attempt in range(30):
        try:
            response = _address_session.post(
                'https://tienich.vnhub.com/api/wards',
                data=payload,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            res_data = response.json()
            
            if res_data.get('success') and res_data.get('data') and len(res_data['data']) > 0 and res_data['data'][0].get('address'):
                converted_addr = res_data['data'][0]['address']
                
                # Tiêu diệt rác API VNHub (VD: trả về chữ "Substates")
                converted_addr = re.sub(r'(?i)\\bsubstates\\b', '', converted_addr)
                converted_addr = re.sub(r',\\s*,', ',', converted_addr) # Xóa dấu phẩy thừa do xóa chữ
                converted_addr = re.sub(r'\\s+', ' ', converted_addr).strip(', ')
                
                return {
                    "original": addr,
                    "success": True,
                    "converted": converted_addr,
                    "source": "vnhub_backup",
                    "_processing_time": time.time() - t0
                }
            
            # Nếu API trả về data rỗng, có thể do Rate Limit ngầm từ VNHub
            # Ngủ 2s rồi thử lại
            if attempt < 29:
                time.sleep(2)
                continue
            break
            
        except Exception as e:
            vnhub_exception = e
            # Lỗi 500 hoặc mạng → thử lại sau 1s
            if attempt < 29:
                time.sleep(1)
                continue
            break  # hết 30 lần
            
    err_primary = str(last_exception) if last_exception else "Geovina data rỗng"
    err_backup = str(vnhub_exception) if vnhub_exception else "VNHub data rỗng"
    
    return {
        "original": addr,
        "success": False,
        "error": f"Lỗi kết nối API: Geovina ({err_primary}); VNHub backup cũng lỗi ({err_backup})",
        "_processing_time": time.time() - t0
    }
"""

start_marker = "    # Retry tối đa 100 lần đối với lỗi mạng/500"
end_marker = "                \"_processing_time\": time.time() - t0\n            }"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx) + len(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement.strip('\n') + content[end_idx:]
    with open('/Users/dangvo/Projects/cccd-qr-excel/wizard/main.py', 'w') as f:
        f.write(new_content)
    print("Successfully replaced.")
else:
    print("Could not find markers.")
