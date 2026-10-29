import pandas as pd
import glob
import os

exports_dir = 'exports'
export_files = glob.glob(os.path.join(exports_dir, '*.xlsx'))
if export_files:
    df = pd.read_excel(export_files[0])
    print(df.columns.tolist())
