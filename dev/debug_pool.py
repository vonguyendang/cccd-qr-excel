import sys, os, time
import concurrent.futures
sys.path.append('/Users/dangvo/Projects/cccd-qr-excel')

from wizard.main import run_extract_new

# We will just import the inner function using a trick, or we can just copy it.
# Actually, let's just write a script that runs the exact same function.
# Wait, I can just patch `ws.iter_rows` to do nothing so we can see if it's the OCR hanging.

