#!/bin/bash
echo "n" | /Users/dangvo/Projects/cccd-qr-excel/.venv/bin/python wizard/main.py --input /Users/dangvo/DATA/THAOPHAM/CCCD_22062026_Sang_10h33/158.jpg --no-gui > output2.log 2>&1 &
PID=$!
echo "Started main.py with PID $PID"

# Đợi 40 giây cho quá trình OCR chạy qua giai đoạn import
sleep 40

echo "Checking if it is still running..."
if ps -p $PID > /dev/null
then
   echo "Sampling PID $PID..."
   sample $PID 1 10 -file sample2_output.txt
   kill -9 $PID
   echo "Sample done."
else
   echo "Process already finished."
fi
