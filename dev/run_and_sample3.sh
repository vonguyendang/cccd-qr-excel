#!/bin/bash
rm -f output3.log sample3_output.txt
echo -e "n\nn\n4\ny\n" | /Users/dangvo/Projects/cccd-qr-excel/.venv/bin/python wizard/main.py /tmp/cccd_test > output3.log 2>&1 &
PID=$!
echo "Started main.py with PID $PID"

sleep 45

echo "Checking if it is still running..."
if ps -p $PID > /dev/null
then
   echo "Sampling PID $PID..."
   sample $PID 1 10 -file sample3_output.txt
   kill -9 $PID
   echo "Sample done."
else
   echo "Process already finished."
fi
