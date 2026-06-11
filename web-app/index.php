<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CCCD QR Excel - Web App</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- jsQR library for reading QR on frontend -->
    <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
    <!-- heic2any library for HEIC support -->
    <script src="https://cdn.jsdelivr.net/npm/heic2any@0.0.4/dist/heic2any.min.js"></script>
    <!-- Tesseract.js for OCR support -->
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>Xử lý ảnh CCCD hàng loạt</h1>
        <p>Ứng dụng sẽ quét mã QR ngay trên trình duyệt (để giảm tải server), sau đó gửi dữ liệu lên server để chuẩn hóa địa chỉ và xuất file Excel.</p>
        
        <div class="upload-area" id="uploadArea">
            <input type="file" id="fileInput" multiple accept="image/*" class="file-input">
            <label for="fileInput" class="upload-label">
                <span>Nhấn vào đây để chọn thư mục/file ảnh CCCD</span><br>
                <small>(Hỗ trợ chọn nhiều file cùng lúc)</small>
            </label>
        </div>

        <div id="statusSection" class="status-section hidden">
            <h3>Tiến trình quét QR cục bộ: <span id="progressText">0/0</span></h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="log-container" id="logContainer"></div>
        </div>

        <div id="serverSection" class="server-section hidden">
            <h3 id="serverStatusText">Đang gửi dữ liệu lên server xử lý...</h3>
            <div id="downloadArea" class="hidden">
                <a href="#" id="downloadLink" class="btn-download">Tải file Excel kết quả</a>
            </div>
        </div>
    </div>

    <script src="assets/js/app.js"></script>
</body>
</html>
