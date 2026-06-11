const SUCCESS_BEEP = 'data:audio/mp3;base64,//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq';
const ERROR_BEEP = 'data:audio/mp3;base64,//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq';

const successAudio = new Audio(SUCCESS_BEEP);
const errorAudio = new Audio(ERROR_BEEP);

// I will use short real beep sounds in the next step, for now placeholder
successAudio.src = 'https://actions.google.com/sounds/v1/alarms/beep_short.ogg';
errorAudio.src = 'https://actions.google.com/sounds/v1/alarms/error_beep.ogg';

document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const tabCameraBtn = document.getElementById('tabCameraBtn');
    const tabFileBtn = document.getElementById('tabFileBtn');
    const cameraSection = document.getElementById('cameraSection');
    const fileSection = document.getElementById('fileSection');
    
    const fileInput = document.getElementById('fileInput');
    const statusSection = document.getElementById('statusSection');
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');
    const logContainer = document.getElementById('logContainer');
    
    const scannedListSection = document.getElementById('scannedListSection');
    const scannedUl = document.getElementById('scannedUl');
    const scanCount = document.getElementById('scanCount');
    const btnProcessAll = document.getElementById('btnProcessAll');
    
    const serverSection = document.getElementById('serverSection');
    const serverStatusText = document.getElementById('serverStatusText');
    const serverSpinner = document.getElementById('serverSpinner');
    const downloadArea = document.getElementById('downloadArea');
    const downloadLink = document.getElementById('downloadLink');
    const toastContainer = document.getElementById('toastContainer');

    let html5QrcodeScanner = null;
    let scannedResults = []; // Stores the final payload objects
    let recentScans = new Set(); // Prevent duplicate scans in short timeframe
    
    // Toast Notification
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-green-500' : (type === 'error' ? 'bg-red-500' : 'bg-blue-500');
        toast.className = `toast flex items-center p-3 mb-2 text-white rounded-lg shadow-lg ${bgColor}`;
        toast.innerHTML = `<span class="font-semibold text-sm">${message}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // Load from cache on startup
    const cachedData = localStorage.getItem('cccd_scanned_results');
    if (cachedData) {
        try {
            const parsed = JSON.parse(cachedData);
            if (Array.isArray(parsed) && parsed.length > 0) {
                scannedResults = parsed;
                scannedListSection.classList.remove('hidden');
                scanCount.textContent = scannedResults.length;
                // render in reverse so they prepend in correct order or just append
                parsed.forEach(item => {
                    renderScannedItemDOM(item);
                });
            }
        } catch(e) {
            console.error('Lỗi khi tải cache', e);
        }
    }

    function playBeep(type) {
        if (type === 'success') {
            successAudio.currentTime = 0;
            successAudio.play().catch(e=>console.log(e));
        } else {
            errorAudio.currentTime = 0;
            errorAudio.play().catch(e=>console.log(e));
        }
    }

    function log(message) {
        const div = document.createElement('div');
        div.textContent = `> ${message}`;
        logContainer.appendChild(div);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    function saveToCache() {
        localStorage.setItem('cccd_scanned_results', JSON.stringify(scannedResults));
    }

    function renderScannedItemDOM(dataObj) {
        const li = document.createElement('li');
        li.className = 'p-3 flex justify-between items-center hover:bg-gray-800 transition-colors';
        
        let label = dataObj.filename;
        if (dataObj.qrData) {
            // parse basic info for display
            const parts = dataObj.qrData.split('|');
            if(parts.length >= 4) {
                label = `${parts[2]} (${parts[0]})`;
            }
        } else if (dataObj.ocrData && dataObj.ocrData['CCCD']) {
            label = `${dataObj.ocrData['Họ tên']} (${dataObj.ocrData['CCCD']}) [OCR]`;
        }

        li.innerHTML = `
            <div class="flex items-center space-x-3">
                <span class="w-2 h-2 rounded-full ${dataObj.error ? 'bg-red-500' : 'bg-green-500'}"></span>
                <span class="text-sm font-medium text-gray-300">${label}</span>
            </div>
            ${dataObj.error ? `<span class="text-xs text-red-400 bg-red-900/30 px-2 py-1 rounded border border-red-800">${dataObj.error}</span>` : ''}
        `;
        scannedUl.prepend(li);
    }

    function addScannedItem(dataObj) {
        scannedResults.push(dataObj);
        scanCount.textContent = scannedResults.length;
        scannedListSection.classList.remove('hidden');
        renderScannedItemDOM(dataObj);
        saveToCache();
    }

    // --- Tab Logic ---
    function switchTab(tab) {
        if (tab === 'camera') {
            tabCameraBtn.classList.add('active');
            tabFileBtn.classList.remove('active');
            cameraSection.classList.remove('hidden');
            fileSection.classList.add('hidden');
            startCamera();
        } else {
            tabFileBtn.classList.add('active');
            tabCameraBtn.classList.remove('active');
            fileSection.classList.remove('hidden');
            cameraSection.classList.add('hidden');
            stopCamera();
        }
    }

    tabCameraBtn.addEventListener('click', () => switchTab('camera'));
    tabFileBtn.addEventListener('click', () => switchTab('file'));

    // --- Camera Scanner Logic ---
    function onScanSuccess(decodedText, decodedResult) {
        // Debounce
        if (recentScans.has(decodedText)) return;
        
        // Check if it looks like CCCD QR (usually contains |)
        if (!decodedText.includes('|')) {
            recentScans.add(decodedText);
            playBeep('error');
            showToast('Mã QR không hợp lệ!', 'error');
            setTimeout(() => recentScans.delete(decodedText), 3000);
            return;
        }

        recentScans.add(decodedText);
        playBeep('success');
        showToast('Đã quét thành công 1 thẻ!', 'success');

        addScannedItem({
            filename: 'Camera_Scan_' + Date.now() + '.jpg',
            qrData: decodedText,
            error: null,
            fromOCR: false
        });

        // Flash effect
        const reader = document.getElementById('reader');
        reader.style.boxShadow = '0 0 30px #2ecc71';
        setTimeout(() => reader.style.boxShadow = 'none', 500);

        // Keep it in memory so we don't scan it again immediately
        setTimeout(() => recentScans.delete(decodedText), 5000);
    }

    function onScanFailure(error) {
        // mostly ignore these as they happen every frame
    }

    function startCamera() {
        if (!html5QrcodeScanner) {
            html5QrcodeScanner = new Html5QrcodeScanner("reader", { 
                fps: 10, 
                qrbox: {width: 250, height: 250},
                aspectRatio: 1.0,
                showTorchButtonIfSupported: true
            }, false);
            html5QrcodeScanner.render(onScanSuccess, onScanFailure);
        }
    }

    function stopCamera() {
        if (html5QrcodeScanner) {
            html5QrcodeScanner.clear().catch(error => {
                console.error("Failed to clear html5QrcodeScanner. ", error);
            });
            html5QrcodeScanner = null;
        }
    }

    // --- File Upload Logic ---
    fileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        statusSection.classList.remove('hidden');
        logContainer.innerHTML = '';
        
        const total = files.length;
        let processedCount = 0;

        log(`Bắt đầu xử lý ${total} file...`);

        const readFileAsImage = async (file) => {
            if (file.name.toLowerCase().endsWith('.heic') || file.type === 'image/heic') {
                log(`   -> Chuyển đổi định dạng HEIC...`);
                try {
                    const blob = await heic2any({ blob: file, toType: "image/jpeg", quality: 0.8 });
                    file = Array.isArray(blob) ? blob[0] : blob;
                } catch (err) {
                    throw new Error(`Lỗi chuyển đổi HEIC: ${err.message}`);
                }
            }
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const img = new Image();
                    img.onload = () => resolve(img);
                    img.onerror = reject;
                    img.src = event.target.result;
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        };

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        // Use ZXing from CDN directly if available, fallback to tesseract OCR
        let codeReader = null;
        if (typeof ZXing !== 'undefined') {
            codeReader = new ZXing.BrowserQRCodeReader();
        }

        for (let i = 0; i < total; i++) {
            const file = files[i];
            log(`[${i+1}/${total}] Đang đọc: ${file.name}`);
            
            let dataObj = { filename: file.name, qrData: null, error: null, fromOCR: false };

            try {
                const img = await readFileAsImage(file);
                
                let foundQR = false;
                if (codeReader) {
                    try {
                        const result = await codeReader.decodeFromImageElement(img);
                        dataObj.qrData = result.text;
                        foundQR = true;
                        log(`-> Tìm thấy mã QR bằng ZXing.`);
                    } catch(e) {
                        // ZXing failed
                    }
                }
                
                if (!foundQR) {
                    log(`-> Đang nhờ AI Backend (WeChat QR) xử lý ảnh khó...`);
                    try {
                        const response = await fetch('process.php?action=scan_qr', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ imageBase64: img.src })
                        });
                        const res = await response.json();
                        if (res.success && res.data) {
                            dataObj.qrData = res.data;
                            foundQR = true;
                            log(`-> Tìm thấy mã QR bằng AI Backend.`);
                        }
                    } catch(e) {
                        log(`-> AI Backend không thể đọc mã QR.`);
                    }
                }
                
                if (!foundQR) {
                    log(`-> Đang thử OCR...`);
                    try {
                        const { data: { text } } = await Tesseract.recognize(img, 'vie');
                        let ocrData = { 'CCCD': '', 'Họ tên': '', 'Ngày sinh': '', 'Giới tính': '', 'Ngày cấp CCCD': '' };
                        
                        const cccdMatch = text.match(/\b\d{12}\b/);
                        if (cccdMatch) ocrData['CCCD'] = cccdMatch[0];
                        
                        // Heuristics mapping (simplified)
                        if (/\bNam\b/i.test(text)) ocrData['Giới tính'] = 'Nam';
                        else if (/\bN[uưứữ][\s]*\b/i.test(text) || /\bNữ\b/i.test(text)) ocrData['Giới tính'] = 'Nữ';
                        
                        dataObj.ocrData = ocrData;
                        dataObj.fromOCR = true;
                        log(`-> Quét OCR hoàn tất.`);
                    } catch (ocrErr) {
                        dataObj.error = "Lỗi xử lý ảnh / Không tìm thấy QR";
                    }
                }
            } catch (err) {
                dataObj.error = "Lỗi đọc file: " + err.message;
            }

            if (!dataObj.error) {
                playBeep('success');
            } else {
                playBeep('error');
            }
            addScannedItem(dataObj);

            processedCount++;
            progressText.textContent = `${processedCount}/${total}`;
            progressFill.style.width = `${(processedCount / total) * 100}%`;
        }

        log(`Hoàn tất đọc ${total} file.`);
        showToast(`Đã tải lên và đọc xong ${total} file`, 'success');
        
        // Reset input so same file can be selected again if needed
        fileInput.value = '';
    });

    // --- Submit to Server ---
    btnProcessAll.addEventListener('click', async () => {
        if (scannedResults.length === 0) {
            showToast('Chưa có dữ liệu nào để xuất!', 'error');
            return;
        }

        serverSection.classList.remove('hidden');
        serverSpinner.classList.remove('hidden');
        serverStatusText.textContent = 'Đang gửi dữ liệu lên server xử lý API chuẩn hóa và tạo Excel...';
        downloadArea.classList.add('hidden');
        
        try {
            const response = await fetch('process.php', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: scannedResults })
            });

            const resData = await response.json();
            
            serverSpinner.classList.add('hidden');

            if (resData.success) {
                serverStatusText.textContent = 'Xử lý thành công! File Excel đã sẵn sàng.';
                serverStatusText.classList.replace('text-blue-300', 'text-green-400');
                downloadArea.classList.remove('hidden');
                downloadLink.href = resData.downloadUrl;
                showToast('Tạo Excel thành công!', 'success');
                playBeep('success');
                
                // Clear state
                scannedResults = [];
                localStorage.removeItem('cccd_scanned_results');
                scannedUl.innerHTML = '';
                scanCount.textContent = '0';
            } else {
                serverStatusText.textContent = `Lỗi server: ${resData.message}`;
                serverStatusText.classList.replace('text-blue-300', 'text-red-400');
                playBeep('error');
            }
        } catch (error) {
            serverSpinner.classList.add('hidden');
            serverStatusText.textContent = `Lỗi kết nối: ${error.message}`;
            serverStatusText.classList.replace('text-blue-300', 'text-red-400');
            playBeep('error');
        }
    });

    const btnClear = document.getElementById('btnClear');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if (confirm('Bạn có chắc chắn muốn xóa toàn bộ danh sách đã quét không?')) {
                scannedResults = [];
                localStorage.removeItem('cccd_scanned_results');
                scannedUl.innerHTML = '';
                scanCount.textContent = '0';
                scannedListSection.classList.add('hidden');
                showToast('Đã làm mới danh sách!', 'success');
            }
        });
    }

    // Initialize Camera as default
    startCamera();
});
