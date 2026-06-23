import sys
import os
import cv2

sys.path.append("/Users/dangvo/Projects/cccd-qr-excel")
import debug_address_v15

test_files = [
    "/Users/dangvo/Projects/cccd-qr-excel/samples/14.JPG",
    "/Users/dangvo/Projects/cccd-qr-excel/samples/z7944591757708_2d723f611c580a8764026ab8435719dc.jpg"
]

with open("/Users/dangvo/Projects/cccd-qr-excel/address_test_log.txt", "w", encoding="utf-8") as f:
    for path in test_files:
        f.write("="*50 + "\n")
        f.write(f"Processing: {os.path.basename(path)}\n")
        img = cv2.imread(path)
        if img is None:
            f.write("Failed to load image.\n")
            continue
        
        _, address, status, log_info = debug_address_v15.extract_address_v15(img)
        
        if "Fallback" in status:
            f.write(f"[Status]          {status}\n")
        else:
            raw_anchor = log_info.get("raw_anchor", "")
            candidate_lines = log_info.get("candidate_lines", [])
            total_score = log_info.get("total_score", 0)
            final_address = log_info.get("final_address", "")
            
            f.write(f"[Raw Anchor]      {raw_anchor}\n")
            f.write(f"[Candidate Lines] {candidate_lines}\n")
            f.write(f"[Total Score]     {total_score}\n")
            f.write(f"[Final Address]   {final_address}\n")
            f.write(f"[Status]          {status}\n")
    f.write("="*50 + "\n")
