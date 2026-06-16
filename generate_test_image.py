import os
from PIL import Image, ImageDraw, ImageFont

def create_dummy_cccd():
    # Kích thước ảnh
    width, height = 800, 500
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    text = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
CĂN CƯỚC CÔNG DÂN
Số / No: 086196005585
Họ và tên / Full name: PHẠM VY THẢO
Ngày sinh / Date of birth: 19/09/1996
Giới tính / Sex: Nữ
Quê quán / Place of origin: An Giang
Nơi thường trú: Tổ 11, Ấp An Thạnh, An Giang"""

    # We might not have a TTF font on Mac easily, but we can try to use a default or generic
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except:
        font = ImageFont.load_default()

    draw.text((50, 50), text, fill='black', font=font)
    img.save("dummy_cccd.jpg")
    print("Created dummy_cccd.jpg")

if __name__ == "__main__":
    create_dummy_cccd()
