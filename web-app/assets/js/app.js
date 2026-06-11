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
                
                // Bỏ qua ZXing trên trình duyệt cho file upload vì ảnh độ phân giải cao sẽ làm treo cứng giao diện.
                // Chuyển thẳng xuống AI Backend xử lý.
                if (!foundQR) {
                    log(`-> Đang nhờ AI Backend (WeChat QR) xử lý ảnh khó...`);
                    try {
                        const response = await fetch('/api/scan_qr', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ imageBase64: img.src, filename: file.name })
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
            const response = await fetch('/api/export', {
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
                clearCache();
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
                clearCache();
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
