const SUCCESS_BEEP = 'data:audio/mp3;base64,//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq';
const ERROR_BEEP = 'data:audio/mp3;base64,//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NExAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq';

const successAudio = new Audio(SUCCESS_BEEP);
const errorAudio = new Audio(ERROR_BEEP);

// I will use short real beep sounds in the next step, for now placeholder
successAudio.src = 'https://actions.google.com/sounds/v1/alarms/beep_short.ogg';
errorAudio.src = 'https://actions.google.com/sounds/v1/alarms/error_beep.ogg';
successAudio.volume = APP_CONFIG.successBeepVolume;
errorAudio.volume = APP_CONFIG.errorBeepVolume;

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
    const btnCancelImport = document.getElementById('btnCancelImport');
    
    let isImportCancelled = false;
    let fileQueue = [];
    let isProcessingQueue = false;
    let totalFilesInQueue = 0;
    let processedCountInQueue = 0;
    
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
                scanCount.textContent = scannedResults.length;
                document.getElementById('emptyState').classList.add('hidden');
                btnProcessAll.disabled = false;
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
        
        // Push Camera logs to Server Terminal
        if (message.includes("[Camera]")) {
            fetch(APP_CONFIG.apiUrl + '/api/log_camera', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            }).catch(e => console.log('Failed to send log to server:', e));
        }
    }

    function saveToCache() {
        localStorage.setItem('cccd_scanned_results', JSON.stringify(scannedResults));
    }

    const formatDate = d => (d && d.length === 8) ? d.slice(0,2)+'/'+d.slice(2,4)+'/'+d.slice(4,8) : d;

    function renderScannedItemDOM(dataObj) {
        const li = document.createElement('li');
        li.className = 'result-card p-4 rounded-xl flex flex-col gap-3';
        
        let headerLabel = dataObj.filename || "Mã QR / Hình ảnh";
        let icon = '<svg class="w-8 h-8 text-indigo-400 p-1.5 bg-indigo-500/10 rounded-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>';
        let detailsHtml = '';
        let notes = [];
        if (dataObj.error) notes.push(dataObj.error);

        if (dataObj.qrData) {
            const parts = dataObj.qrData.split('|');
            if (parts.length < 7 || !parts[6]) notes.push('Thiếu ngày cấp');
            if (parts.length < 6 || !parts[5]) notes.push('Thiếu nơi thường trú');

            if(parts.length >= 7) {
                headerLabel = `<div class="font-bold text-slate-200 text-lg">${parts[2]}</div><div class="text-xs text-slate-400 mt-1 font-mono">${parts[0]}</div>`;
                icon = '<svg class="w-8 h-8 text-emerald-400 p-1.5 bg-emerald-500/10 rounded-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';
                
                detailsHtml = `
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm mt-2 pt-3 border-t border-slate-700/50">
                        <div><span class="text-slate-500">CMND:</span> <span class="text-slate-300 font-mono">${parts[1] || '-'}</span></div>
                        <div><span class="text-slate-500">Giới tính:</span> <span class="text-slate-300">${parts[4] || '-'}</span></div>
                        <div><span class="text-slate-500">Ngày sinh:</span> <span class="text-slate-300">${formatDate(parts[3]) || '-'}</span></div>
                        <div><span class="text-slate-500">Ngày cấp:</span> <span class="text-slate-300">${formatDate(parts[6]) || '-'}</span></div>
                        <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Thường trú gốc:</span> <span class="text-slate-300 leading-snug">${parts[5] || '-'}</span></div>
                        
                        <div class="col-span-1 md:col-span-2 border-t border-slate-700/30 pt-2 mt-1"></div>
                        <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Đ/c chuẩn hóa:</span> <span class="text-indigo-400 italic text-xs">Sẽ được xử lý và đồng bộ khi bấm Xuất Excel</span></div>
                        <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Ghi chú:</span> <span class="${notes.length > 0 ? 'text-red-400 font-medium' : 'text-slate-400'}">${notes.join('; ') || '-'}</span></div>
                        <div class="col-span-1 md:col-span-2"><span class="text-slate-500">QR Raw:</span> <span class="text-slate-500 font-mono text-[10px] break-all block mt-1 bg-black/30 p-2 rounded">${dataObj.qrData}</span></div>
                    </div>
                `;
            } else if (parts.length > 0) {
                 headerLabel = `<div class="font-bold text-slate-200">${parts[2] || 'Không xác định'}</div><div class="text-xs text-slate-400 mt-1 font-mono">${parts[0]}</div>`;
                 icon = '<svg class="w-8 h-8 text-emerald-400 p-1.5 bg-emerald-500/10 rounded-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';
                 detailsHtml = `<div class="mt-2 text-xs text-slate-500 font-mono break-all bg-black/30 p-2 rounded">QR Raw: ${dataObj.qrData}</div>`;
            }
        } else if (dataObj.ocrData && dataObj.ocrData['CCCD']) {
            const ocr = dataObj.ocrData;
            if (!ocr['Ngày cấp CCCD']) notes.push('Thiếu ngày cấp');
            if (!ocr['Nơi thường trú gốc']) notes.push('Thiếu nơi thường trú');
            notes.push('Lấy bằng OCR');

            headerLabel = `<div class="font-bold text-slate-200 text-lg">${ocr['Họ tên']}</div><div class="text-xs text-yellow-400 mt-1 font-mono">${ocr['CCCD']} [Lấy bằng OCR]</div>`;
            icon = '<svg class="w-8 h-8 text-yellow-400 p-1.5 bg-yellow-500/10 rounded-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>';
            
            detailsHtml = `
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm mt-2 pt-3 border-t border-slate-700/50">
                    <div><span class="text-slate-500">CMND:</span> <span class="text-slate-300 font-mono">${ocr['CMND'] || '-'}</span></div>
                    <div><span class="text-slate-500">Giới tính:</span> <span class="text-slate-300">${ocr['Giới tính'] || '-'}</span></div>
                    <div><span class="text-slate-500">Ngày sinh:</span> <span class="text-slate-300">${ocr['Ngày sinh'] || '-'}</span></div>
                    <div><span class="text-slate-500">Ngày cấp:</span> <span class="text-slate-300">${ocr['Ngày cấp CCCD'] || '-'}</span></div>
                    <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Thường trú gốc:</span> <span class="text-slate-300 leading-snug">${ocr['Nơi thường trú gốc'] || '-'}</span></div>
                    
                    <div class="col-span-1 md:col-span-2 border-t border-slate-700/30 pt-2 mt-1"></div>
                    <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Đ/c chuẩn hóa:</span> <span class="text-indigo-400 italic text-xs">Sẽ được xử lý và đồng bộ khi bấm Xuất Excel</span></div>
                    <div class="col-span-1 md:col-span-2"><span class="text-slate-500">Ghi chú:</span> <span class="text-yellow-500 font-medium">${notes.join('; ') || '-'}</span></div>
                    <div class="col-span-1 md:col-span-2"><span class="text-slate-500">QR Raw:</span> <span class="text-slate-500 italic text-xs">-</span></div>
                </div>
            `;
        }

        li.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex items-center space-x-4">
                    ${icon}
                    <div>
                        ${headerLabel}
                    </div>
                </div>
            </div>
            ${detailsHtml}
        `;
        scannedUl.prepend(li);
    }

    function isDuplicateCccd(dataObj) {
        if (!dataObj) return false;
        let newCccd = null;
        let isNewQR = !!dataObj.qrData;

        if (dataObj.qrData) {
            newCccd = dataObj.qrData.split('|')[0];
        } else if (dataObj.ocrData && dataObj.ocrData['CCCD']) {
            newCccd = dataObj.ocrData['CCCD'];
        }
        if (!newCccd) return false;
        
        let dupIndex = scannedResults.findIndex(item => {
            let existingCccd = null;
            if (item.qrData) existingCccd = item.qrData.split('|')[0];
            else if (item.ocrData && item.ocrData['CCCD']) existingCccd = item.ocrData['CCCD'];
            return existingCccd === newCccd;
        });

        if (dupIndex !== -1) {
            let existingItem = scannedResults[dupIndex];
            let isExistingQR = !!existingItem.qrData;

            // If new is QR and existing is OCR, we remove the OCR one to replace it with QR!
            if (isNewQR && !isExistingQR) {
                scannedResults.splice(dupIndex, 1);
                // Re-render UI
                const scannedUl = document.getElementById('scannedUl');
                scannedUl.innerHTML = '';
                const temp = [...scannedResults];
                temp.reverse().forEach(item => renderScannedItemDOM(item));
                return false; // Proceed to add the new QR item
            }
            return true; // Otherwise it's a true duplicate, skip it
        }
        return false;
    }

    function addScannedItem(dataObj) {
        scannedResults.push(dataObj);
        scanCount.textContent = scannedResults.length;
        document.getElementById('emptyState').classList.add('hidden');
        btnProcessAll.disabled = false;
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
        
        statusSection.classList.remove('hidden');
        
        // Check if it looks like CCCD QR (usually contains |)
        if (!decodedText.includes('|')) {
            recentScans.add(decodedText);
            playBeep('error');
            showToast('Mã QR không hợp lệ!', 'error');
            log(`[Camera] Phát hiện mã QR nhưng không đúng định dạng CCCD.`);
            setTimeout(() => recentScans.delete(decodedText), 3000);
            return;
        }

        const dataObj = {
            filename: 'Camera_Scan_' + Date.now() + '.jpg',
            qrData: decodedText,
            error: null,
            fromOCR: false
        };

        if (isDuplicateCccd(dataObj)) {
            recentScans.add(decodedText);
            showToast('Thẻ này đã được quét rồi!', 'warning');
            log(`[Camera] Bỏ qua thẻ trùng: CCCD ${dataObj.qrData.split('|')[0]}`);
            setTimeout(() => recentScans.delete(decodedText), 3000);
            return;
        }

        recentScans.add(decodedText);
        playBeep('success');
        showToast('Đã quét thành công 1 thẻ!', 'success');
        log(`[Camera] Quét thành công CCCD: ${dataObj.qrData.split('|')[0]}`);
        addScannedItem(dataObj);
        
        // Auto-scroll to results on mobile
        if (window.innerWidth < 1024) {
            document.getElementById('scannedUlContainer').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

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
                fps: 20, 
                qrbox: function(viewfinderWidth, viewfinderHeight) {
                    // Responsive qrbox based on screen size, CCCD QR is usually small
                    let minEdgePercentage = 0.7; // 70% of min edge
                    let minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
                    let qrboxSize = Math.floor(minEdgeSize * minEdgePercentage);
                    return { width: qrboxSize, height: qrboxSize };
                },
                aspectRatio: 1.0,
                formatsToSupport: [ Html5QrcodeSupportedFormats.QR_CODE ],
                showTorchButtonIfSupported: true
            }, false);
            html5QrcodeScanner.render(onScanSuccess, onScanFailure);
        }
        document.getElementById('scanLineAnim').classList.remove('hidden');
    }

    function stopCamera() {
        if (html5QrcodeScanner) {
            html5QrcodeScanner.clear().catch(error => {
                console.error("Failed to clear html5QrcodeScanner. ", error);
            });
            html5QrcodeScanner = null;
        }
        document.getElementById('scanLineAnim').classList.add('hidden');
    }

    // --- File Upload Logic ---
    if (btnCancelImport) {
        btnCancelImport.addEventListener('click', () => {
            isImportCancelled = true;
            log(`[Hệ thống] Đang dừng lệnh quét file...`);
            btnCancelImport.classList.add('hidden');
        });
    }

    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;
        
        fileQueue.push(...files);
        totalFilesInQueue += files.length;
        
        if (isProcessingQueue) {
            log(`[Hệ thống] Đã thêm ${files.length} file vào hàng chờ (Đang đợi: ${fileQueue.length} file)...`);
            // Update progress bar max
            progressText.textContent = `${processedCountInQueue}/${totalFilesInQueue}`;
            progressFill.style.width = `${(processedCountInQueue / totalFilesInQueue) * 100}%`;
            fileInput.value = ''; // Reset
            return;
        }
        
        isProcessingQueue = true;
        isImportCancelled = false;
        btnCancelImport.classList.remove('hidden');

        statusSection.classList.remove('hidden');
        logContainer.innerHTML = '';
        
        log(`Bắt đầu xử lý hàng chờ gồm ${totalFilesInQueue} file...`);

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

        const resizeImage = (img, maxSize) => {
            let width = img.width;
            let height = img.height;
            if (width > height && width > maxSize) {
                height = Math.round(height * maxSize / width);
                width = maxSize;
            } else if (height > maxSize) {
                width = Math.round(width * maxSize / height);
                height = maxSize;
            } else {
                return img.src; // No resize needed
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            return canvas.toDataURL('image/jpeg', 0.8);
        };

        const processImage = async (file, index) => {
            if (scannedResults.some(item => item.filename === file.name && !item.error)) {
                log(`[${index+1}/${totalFilesInQueue}] Bỏ qua ${file.name}: Đã có trong bộ đệm (trùng tên file).`);
                processedCountInQueue++;
                progressText.textContent = `${processedCountInQueue}/${totalFilesInQueue}`;
                progressFill.style.width = `${(processedCountInQueue / totalFilesInQueue) * 100}%`;
                return;
            }

            log(`[${index+1}/${totalFilesInQueue}] Bắt đầu xử lý: ${file.name}`);
            let dataObj = { filename: file.name, qrData: null, error: null, fromOCR: false };

            try {
                const img = await readFileAsImage(file);
                // Resize image to max (from config) to drastically reduce payload size and OCR time
                const optimizedBase64 = resizeImage(img, APP_CONFIG.maxImageSize); 
                
                let foundQR = false;
                
                if (!foundQR) {
                    try {
                        const response = await fetch(APP_CONFIG.apiScanQR, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ imageBase64: optimizedBase64, filename: file.name })
                        });
                        const res = await response.json();
                        if (res.success && res.data) {
                            dataObj.qrData = res.data;
                            foundQR = true;
                            log(`[${index+1}/${totalFilesInQueue}] Tìm thấy QR bằng AI Backend.`);
                        }
                    } catch(e) {
                        log(`[${index+1}/${totalFilesInQueue}] Lỗi AI Backend.`);
                    }
                }
                
                if (!foundQR) {
                    log(`[${index+1}/${totalFilesInQueue}] Không tìm thấy QR, đang thử OCR...`);
                    try {
                        // OCR runs on the optimized image, much faster
                        const { data: { text } } = await Tesseract.recognize(optimizedBase64, 'vie');
                        let ocrData = { 'CCCD': '', 'Họ tên': '', 'Ngày sinh': '', 'Giới tính': '', 'Ngày cấp CCCD': '', 'Nơi thường trú gốc': '' };
                        const cccdMatch = text.match(/\b\d{12}\b/);
                        if (cccdMatch) ocrData['CCCD'] = cccdMatch[0];
                        
                        const lines = text.split('\n').map(l => l.trim()).filter(l => l);
                        const allDates = text.match(/\b\d{2}\s*\/\s*\d{2}\s*\/\s*\d{4}\b/g) || [];
                        
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i];
                            const lineLower = line.toLowerCase();
                            
                            // Extract Gender strictly from Gender line
                            if (lineLower.includes("giới tính") || lineLower.includes("sex") || lineLower.includes("gioi tinh") || lineLower.includes("gidi")) {
                                if (lineLower.includes("nữ") || lineLower.includes("nu ") || lineLower.includes("nư")) ocrData['Giới tính'] = 'Nữ';
                                else if (lineLower.includes("nam")) ocrData['Giới tính'] = 'Nam';
                            }
                            
                            // 1. Extract Name
                            if (lineLower.includes("họ và tên") || lineLower.includes("họ chữ đệm") || lineLower.includes("họ, chữ đệm") || lineLower.includes("full name")) {
                                if (line.includes(":")) {
                                    let namePart = line.split(":")[1].replace(/[|]/g, '').trim();
                                    namePart = namePart.replace(/[^\p{L}\s]/gu, '').replace(/\s+/g, ' ').trim();
                                    if (namePart.length > 3) ocrData['Họ tên'] = namePart.toUpperCase();
                                }
                                if (!ocrData['Họ tên'] && i + 1 < lines.length) {
                                    let nextLine = lines[i+1].replace(/\|/g, '').trim();
                                    nextLine = nextLine.replace(/[^\p{L}\s]/gu, '').replace(/\s+/g, ' ').trim();
                                    if (nextLine.length > 3 && !nextLine.toLowerCase().includes("ngày") && !nextLine.toLowerCase().includes("date")) {
                                        ocrData['Họ tên'] = nextLine.toUpperCase();
                                    }
                                }
                            }
                            
                            // 2. Extract DOB
                            if (lineLower.includes("sinh") || lineLower.includes("birth")) {
                                for (let j = i; j <= i+1 && j < lines.length; j++) {
                                    const m = lines[j].match(/\b\d{2}\s*\/\s*\d{2}\s*\/\s*\d{4}\b/);
                                    if (m) { ocrData['Ngày sinh'] = m[0].replace(/\s/g, ''); break; }
                                }
                            }
                            
                            // 3. Extract Address
                            if (lineLower.includes("thường trú") || lineLower.includes("cư trú") || lineLower.includes("residence") || lineLower.includes("cu tru") || lineLower.includes("thuong tru") || lineLower.includes("trú /") || lineLower.includes("tru /")) {
                                let addrParts = [];
                                if (line.includes(":")) addrParts.push(line.split(":")[1].replace(/[|]/g, '').trim());
                                if (i+1 < lines.length && !lines[i+1].toLowerCase().includes("giá trị đến") && !lines[i+1].toLowerCase().includes("expiry")) {
                                    addrParts.push(lines[i+1].replace(/\|/g, '').trim());
                                }
                                if (i+2 < lines.length && !lines[i+2].toLowerCase().includes("giá trị đến") && !lines[i+2].toLowerCase().includes("expiry")) {
                                    const next2 = lines[i+2].replace(/\|/g, '').trim();
                                    if (next2.length > 5 && !next2.match(/\d{2}\s*\/\s*\d{2}\s*\/\s*\d{4}/)) addrParts.push(next2);
                                }
                                ocrData['Nơi thường trú gốc'] = addrParts.filter(p => p).join(', ').replace(/,\s*,/g, ',').replace(/^,\s*/, '');
                            }
                            
                            // 4. Extract Issue Date (Back of card)
                            if (lineLower.includes("ngày, tháng, năm") || lineLower.includes("date, month, year") || lineLower.includes("date of issue") || lineLower.includes("ngay, thang, nam")) {
                                for (let j = i; j <= i+2 && j < lines.length; j++) {
                                    const m = lines[j].match(/\b\d{2}\s*\/\s*\d{2}\s*\/\s*\d{4}\b/);
                                    if (m) { ocrData['Ngày cấp CCCD'] = m[0].replace(/\s/g, ''); break; }
                                }
                            }
                        }
                        
                        // Fallback DOB if keyword failed
                        if (!ocrData['Ngày sinh'] && allDates.length > 0) {
                            const firstDate = allDates[0].replace(/\s/g, '');
                            if (parseInt(firstDate.split('/')[2]) < 2020) ocrData['Ngày sinh'] = firstDate;
                        }
                        
                        // Fallback Gender if keyword failed but Nữ is found anywhere
                        if (!ocrData['Giới tính'] && (text.toLowerCase().includes("nữ") || text.toLowerCase().includes("nư "))) {
                            ocrData['Giới tính'] = 'Nữ';
                        }
                        // Fallback Gender: Nam (if not Việt Nam or other common Nam)
                        if (!ocrData['Giới tính']) {
                            const textLower = text.toLowerCase();
                            // Count occurrences of "nam"
                            const namCount = (textLower.match(/\bnam\b/g) || []).length;
                            const vietNamCount = (textLower.match(/việt nam|viet nam|hà nam|quảng nam|hải nam/g) || []).length;
                            if (namCount > vietNamCount) {
                                ocrData['Giới tính'] = 'Nam';
                            }
                        }
                            

                        
                        dataObj.ocrData = ocrData;
                        dataObj.fromOCR = true;
                        log(`[${index+1}/${totalFilesInQueue}] Quét OCR hoàn tất.`);
                    } catch (ocrErr) {
                        dataObj.error = "Không tìm thấy QR/Lỗi OCR";
                    }
                }
            } catch (err) {
                dataObj.error = "Lỗi đọc file: " + err.message;
            }

            if (!dataObj.error && (dataObj.qrData || dataObj.ocrData['CCCD'])) {
                if (isDuplicateCccd(dataObj)) {
                    log(`[${index+1}/${totalFilesInQueue}] Bỏ qua ${file.name}: Dữ liệu CCCD bị trùng.`);
                } else {
                    playBeep('success');
                    addScannedItem(dataObj);
                }
            } else {
                playBeep('error');
                log(`[${index+1}/${totalFilesInQueue}] Thất bại ${file.name}: ${dataObj.error}`);
            }

            processedCountInQueue++;
            progressText.textContent = `${processedCountInQueue}/${totalFilesInQueue}`;
            progressFill.style.width = `${(processedCountInQueue / totalFilesInQueue) * 100}%`;
        };

        // Run concurrently with a pool of workers defined in config
        const concurrencyLimit = APP_CONFIG.concurrencyLimit;
        const workers = Array(concurrencyLimit).fill(Promise.resolve()).map(async () => {
            while (fileQueue.length > 0) {
                if (isImportCancelled) {
                    fileQueue = []; // Empty queue
                    break;
                }
                const file = fileQueue.shift();
                await processImage(file, processedCountInQueue); // Pass current index just for logging
            }
        });
        
        await Promise.all(workers);

        btnCancelImport.classList.add('hidden');
        isProcessingQueue = false;

        if (isImportCancelled) {
            log(`Đã hủy tiến trình, chỉ quét xong ${processedCountInQueue}/${totalFilesInQueue} file.`);
            showToast(`Đã hủy! Quét được ${processedCountInQueue}/${totalFilesInQueue} file.`, 'error');
        } else {
            log(`Hoàn tất đọc ${totalFilesInQueue} file.`);
            showToast(`Đã tải lên và đọc xong toàn bộ hàng chờ.`, 'success');
        }
        
        // Reset queue counters
        totalFilesInQueue = 0;
        processedCountInQueue = 0;
        
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
            const response = await fetch(APP_CONFIG.apiExportExcel, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: scannedResults })
            });

            serverSpinner.classList.add('hidden');

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                
                // Trích xuất filename từ header Content-Disposition nếu có
                let filename = "ket_qua.xlsx";
                const disposition = response.headers.get('content-disposition');
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    var matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) { 
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                serverStatusText.textContent = 'Xử lý thành công! File Excel đã sẵn sàng.';
                serverStatusText.classList.replace('text-blue-300', 'text-green-400');
                downloadArea.classList.remove('hidden');
                downloadLink.href = url;
                downloadLink.download = filename;
                showToast('Tạo Excel thành công!', 'success');
                playBeep('success');
                
                // Clear state
                scannedResults = [];
                localStorage.removeItem('cccd_scanned_results');
                scannedUl.innerHTML = '';
                scanCount.textContent = '0';
                document.getElementById('emptyState').classList.remove('hidden');
                btnProcessAll.disabled = true;
                showToast('Đã làm mới dữ liệu.', 'success');
            } else {
                serverStatusText.textContent = `Lỗi server: Đã xảy ra lỗi khi tạo Excel.`;
                serverStatusText.classList.replace('text-blue-300', 'text-red-400');
                showToast('Lỗi server', 'error');
                playBeep('error');
            }
        } catch (err) {
            serverSpinner.classList.add('hidden');
            serverStatusText.textContent = `Lỗi kết nối: ${error.message}`;
            serverStatusText.classList.replace('text-blue-300', 'text-red-400');
            playBeep('error');
        }
    });

    const btnClear = document.getElementById('btnClear');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if (confirm('Bạn có chắc muốn xóa toàn bộ danh sách kết quả?')) {
                scannedResults = [];
                localStorage.removeItem('cccd_scanned_results');
                scannedUl.innerHTML = '';
                scanCount.textContent = '0';
                document.getElementById('emptyState').classList.remove('hidden');
                btnProcessAll.disabled = true;
                showToast('Đã làm mới dữ liệu.', 'success');
            }
        });
    }

    // Initialize Camera as default
    startCamera();
});
