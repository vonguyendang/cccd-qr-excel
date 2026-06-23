#!/bin/bash
# Chạy main.py trong nền
/Users/dangvo/Projects/cccd-qr-excel/.venv/bin/python wizard/main.py --input /Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg --no-gui > output.log 2>&1 &
PID=$!
echo "Started main.py with PID $PID"

# Đợi 15 giây cho quá trình OCR bị treo
sleep 15

echo "Sampling PID $PID..."
sample $PID 1 10 -file sample_output.txt

# Giết tiến trình
kill -9 $PID
echo "Done."
