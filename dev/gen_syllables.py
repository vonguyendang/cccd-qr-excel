def generate_vietnamese_syllables():
    # Phụ âm đầu
    initials = ["", "B", "C", "CH", "D", "Đ", "G", "GH", "GI", "H", "K", "KH", "L", "M", "N", "NG", "NGH", "NH", "P", "PH", "Q", "QU", "R", "S", "T", "TH", "TR", "V", "X"]
    # Vần
    rhymes = [
        "A", "AC", "ACH", "AI", "AM", "AN", "ANG", "ANH", "AO", "AP", "AT", "AU", "AY",
        "E", "EC", "EM", "EN", "ENG", "EO", "EP", "ET", "EU",
        "I", "IA", "ICH", "IEP", "IEC", "IEM", "IEN", "IENG", "IET", "IEU", "IM", "IN", "INH", "IP", "IT", "IU",
        "O", "OC", "OI", "OM", "ON", "ONG", "OP", "OT",
        "U", "UC", "UE", "UI", "UM", "UN", "UNG", "UO", "UOC", "UOI", "UOM", "UON", "UONG", "UOP", "UOT", "UOU", "UP", "UT", "UY", "UYA", "UYCH", "UYEN", "UYET", "UYNH", "UYT",
        "Y", "YCH", "YEM", "YEN", "YENG", "YET", "YEU"
    ]
    # Remove duplicates and convert 'Đ' to 'D' since MRZ uses 'D'
    syllables = set()
    for i in initials:
        i = i.replace('Đ', 'D')
        for r in rhymes:
            syllable = i + r
            syllables.add(syllable)
    
    # Also add variations for Ă, Â, Ê, Ô, Ơ, Ư which map to A, E, O, U
    # But rhymes above already cover most unaccented combinations.
    # Let's add common names missing:
    extras = "HOANG HUNG HOA HIEU HIEN THUY TRUC TRUNG PHUONG NGOC NHAN NGUYEN VINH YEN OANH UYEN QUYNH QUANG"
    for e in extras.split(): syllables.add(e)
    
    return sorted(list(syllables), key=len, reverse=True)

s = generate_vietnamese_syllables()
print(f"Total: {len(s)}")
print(f"Example: {s[:10]}")
