import pandas as pd
import glob
import os
from process_excel import remove_accents

exports_dir = 'exports'
export_files = glob.glob(os.path.join(exports_dir, '*.xlsx'))
exports_df_list = []
for f in export_files:
    exports_df_list.append(pd.read_excel(f))
exports_df = pd.concat(exports_df_list, ignore_index=True)

print("Unique Notes:")
print(exports_df['Ghi chú'].unique())

print("\nSample 5 Unaccented Names from exports:")
print(exports_df['Họ tên'].apply(remove_accents).head(5).tolist())

