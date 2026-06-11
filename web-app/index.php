<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CCCD QR Scanner Pro</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/heic2any@0.0.4/dist/heic2any.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>
    <!-- Add Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen font-inter flex flex-col items-center py-10 relative overflow-x-hidden">
    <!-- Background glow effect -->
    <div class="fixed top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/20 blur-[120px] pointer-events-none"></div>
    <div class="fixed bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-600/20 blur-[120px] pointer-events-none"></div>

    <div class="container glass-panel p-8 w-full max-w-4xl relative z-10">
        <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500 mb-2 text-center">Scanner Pro</h1>
        <p class="text-gray-400 text-center mb-8">Hệ thống trích xuất mã QR CCCD tự động</p>
        
        <!-- Tabs -->
        <div class="flex justify-center mb-6 space-x-4">
            <button id="tabCameraBtn" class="tab-btn active px-6 py-2 rounded-full font-semibold transition-all">📸 Live Camera</button>
            <button id="tabFileBtn" class="tab-btn px-6 py-2 rounded-full font-semibold transition-all">📁 Tải Ảnh Lên</button>
        </div>

        <!-- Camera Section -->
        <div id="cameraSection" class="tab-content block">
            <div class="scanner-container rounded-xl overflow-hidden shadow-2xl bg-black/50 border border-white/10 p-2">
                <div id="reader" width="100%"></div>
            </div>
            <p class="text-center text-gray-500 mt-4 text-sm">*Đưa mã QR của CCCD vào giữa khung hình để tự động quét.</p>
        </div>

        <!-- File Upload Section -->
        <div id="fileSection" class="tab-content hidden">
            <div class="upload-area group relative overflow-hidden rounded-2xl border-2 border-dashed border-blue-500/50 hover:border-blue-400 p-12 text-center cursor-pointer transition-all bg-black/30">
                <input type="file" id="fileInput" multiple accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20">
                <div class="relative z-10 flex flex-col items-center justify-center pointer-events-none">
                    <div class="w-16 h-16 mb-4 rounded-full bg-blue-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                    </div>
                    <span class="text-xl font-semibold text-blue-300">Kéo thả hoặc Nhấn để tải ảnh CCCD</span>
                    <small class="text-gray-500 mt-2 block">Hỗ trợ .jpg, .png, .heic (nhiều file cùng lúc)</small>
                </div>
            </div>
        </div>

        <!-- Progress and Status -->
        <div id="statusSection" class="mt-8 hidden">
            <h3 class="text-lg font-semibold mb-2">Đang xử lý ảnh: <span id="progressText" class="text-blue-400">0/0</span></h3>
            <div class="w-full bg-gray-800 rounded-full h-2.5 mb-4 overflow-hidden border border-gray-700">
                <div class="bg-gradient-to-r from-blue-500 to-purple-500 h-2.5 rounded-full transition-all duration-300 ease-out" id="progressFill" style="width: 0%"></div>
            </div>
            <div id="logContainer" class="h-32 overflow-y-auto bg-black/60 rounded-lg p-3 font-mono text-xs text-gray-400 border border-gray-800"></div>
        </div>

        <!-- Realtime Scanned List -->
        <div id="scannedListSection" class="mt-8 hidden">
            <div class="flex justify-between items-end mb-4">
                <h3 class="text-xl font-bold text-white">Danh sách đã quét (<span id="scanCount" class="text-green-400">0</span>)</h3>
                <div class="space-x-2">
                    <button id="btnClear" class="bg-red-600/80 hover:bg-red-500 text-white font-bold py-2 px-4 rounded-lg shadow-lg shadow-red-500/30 transition-all text-sm border border-red-500/50">Làm mới</button>
                    <button id="btnProcessAll" class="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white font-bold py-2 px-6 rounded-lg shadow-lg shadow-green-500/30 transform hover:scale-105 transition-all">Xuất Excel ngay</button>
                </div>
            </div>
            <div class="bg-black/40 border border-gray-700/50 rounded-xl overflow-hidden">
                <ul id="scannedUl" class="max-h-64 overflow-y-auto divide-y divide-gray-800">
                    <!-- Items injected here -->
                </ul>
            </div>
        </div>

        <!-- Server Process Section -->
        <div id="serverSection" class="mt-8 hidden p-6 text-center bg-blue-900/20 border border-blue-500/30 rounded-xl">
            <div class="spinner inline-block w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" id="serverSpinner"></div>
            <h3 id="serverStatusText" class="text-lg font-semibold text-blue-300">Đang chuẩn hóa địa chỉ trên máy chủ...</h3>
            <div id="downloadArea" class="hidden mt-6">
                <a href="#" id="downloadLink" class="inline-flex items-center justify-center bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-400 hover:to-teal-400 text-white font-bold py-3 px-8 rounded-full shadow-xl shadow-green-500/20 transform hover:-translate-y-1 transition-all">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                    Tải File Excel Hoàn Tất
                </a>
            </div>
        </div>
    </div>

    <!-- Toast Notification Container -->
    <div id="toastContainer" class="fixed bottom-5 right-5 flex flex-col gap-2 z-50"></div>

    <script src="assets/js/app.js"></script>
</body>
</html>
