import pandas as pd
import sys
import os
from rich.console import Console

console = Console()
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from wizard.main import call_address_api

def fix_excel_address(excel_path):
    console.print(f"[bold cyan]Đang đọc file Excel:[/bold cyan] {excel_path}")
    
    # Đọc bằng openpyxl để giữ nguyên định dạng nếu có thể, hoặc dùng pandas cho nhanh
    # Dùng pandas đọc và ghi lại là dễ nhất
    df = pd.read_excel(excel_path)
    
    if "Nơi thường trú gốc" not in df.columns or "Địa chỉ chuẩn hóa mới" not in df.columns:
        console.print("[red]Lỗi: File Excel không đúng định dạng (thiếu cột)[/red]")
        return

    # Thu thập các địa chỉ duy nhất
    unique_addrs = df["Nơi thường trú gốc"].dropna().unique().tolist()
    unique_addrs = [a.strip() for a in unique_addrs if str(a).strip()]
    
    console.print(f"Tìm thấy [green]{len(unique_addrs)}[/green] địa chỉ duy nhất. Đang gọi API chuẩn hóa với 4 luồng...")
    
    # Gọi API
    api_results = call_address_api(unique_addrs, max_workers=4)
    
    # Tạo dictionary map
    addr_map = {}
    for res in api_results:
        original = res.get("original")
        if res.get("success"):
            addr_map[original] = res.get("converted")
        else:
            # Nếu vẫn lỗi thì giữ nguyên hoặc để trống
            console.print(f"[yellow]Vẫn lỗi: {original} -> {res.get('error')}[/yellow]")
            addr_map[original] = "" # Hoặc có thể lấy string lỗi

    # Cập nhật DataFrame
    def update_address(row):
        orig = str(row["Nơi thường trú gốc"]).strip() if pd.notna(row["Nơi thường trú gốc"]) else ""
        if orig in addr_map and addr_map[orig]:
            return addr_map[orig]
        return row["Địa chỉ chuẩn hóa mới"] # Giữ nguyên nếu API thất bại

    df["Địa chỉ chuẩn hóa mới"] = df.apply(update_address, axis=1)
    
    # Lưu file
    output_path = excel_path.replace(".xlsx", "_fixed.xlsx")
    df.to_excel(output_path, index=False)
    console.print(f"[bold green]Đã lưu file thành công tại:[/bold green] {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Đường dẫn file Excel")
    args = parser.parse_args()
    fix_excel_address(args.file)
