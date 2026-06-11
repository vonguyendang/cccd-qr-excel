// File cấu hình toàn cục cho Web App
const APP_CONFIG = {
    // Tùy chỉnh hiệu năng
    concurrencyLimit: 4,      // Số lượng ảnh được xử lý song song cùng lúc (Tăng lên nếu CPU/RAM mạnh)
    maxImageSize: 1500,       // Kích thước tối đa (pixel) khi nén ảnh trước khi gửi. Giảm xuống để chạy nhanh hơn nhưng có thể giảm độ chính xác.
    
    // Tùy chỉnh API
    apiScanQR: '/api/scan_qr',
    apiExportExcel: '/api/export',

    // Tùy chỉnh UI/UX
    successBeepVolume: 1.0,   // Âm lượng tiếng bíp thành công (0.0 đến 1.0)
    errorBeepVolume: 1.0      // Âm lượng tiếng bíp lỗi (0.0 đến 1.0)
};
