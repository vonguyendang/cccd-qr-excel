import sys
import os
import cv2
import json
from pyzbar.pyzbar import decode, ZBarSymbol

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': 'No image path provided'}))
        return

    img_path = sys.argv[1]
    if not os.path.exists(img_path):
        print(json.dumps({'success': False, 'error': 'File not found'}))
        return

    img = cv2.imread(img_path)
    if img is None:
        print(json.dumps({'success': False, 'error': 'Cannot read image'}))
        return

    # Try zbar first
    decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE])
    if not decoded_objects:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        decoded_objects = decode(gray, symbols=[ZBarSymbol.QRCODE])
    
    if decoded_objects:
        print(json.dumps({'success': True, 'data': decoded_objects[0].data.decode('utf-8')}))
        return

    # Try WeChat
    model_paths = [
        'models/detect.prototxt', 'models/detect.caffemodel',
        'models/sr.prototxt', 'models/sr.caffemodel'
    ]
    
    try:
        # Resolve absolute paths based on this script's location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_model_paths = [os.path.join(base_dir, p) for p in model_paths]
        
        detector = cv2.wechat_qrcode_WeChatQRCode(*abs_model_paths)
        res, _ = detector.detectAndDecode(img)
        if res and len(res) > 0:
            print(json.dumps({'success': True, 'data': res[0]}))
            return
    except Exception as e:
        pass
        
    print(json.dumps({'success': False, 'error': 'QR code not found'}))

if __name__ == '__main__':
    main()
