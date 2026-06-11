document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const statusSection = document.getElementById('statusSection');
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');
    const logContainer = document.getElementById('logContainer');
    const serverSection = document.getElementById('serverSection');
    const serverStatusText = document.getElementById('serverStatusText');
    const downloadArea = document.getElementById('downloadArea');
    const downloadLink = document.getElementById('downloadLink');

    function log(message) {
        const div = document.createElement('div');
        div.textContent = message;
        logContainer.appendChild(div);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    fileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        // Reset UI
        statusSection.classList.remove('hidden');
        serverSection.classList.add('hidden');
        downloadArea.classList.add('hidden');
        logContainer.innerHTML = '';
        
        const total = files.length;
        let processedCount = 0;
        const results = [];

        log(`Bắt đầu xử lý ${total} file...`);

        // Helper function to read file as Image
        const readFileAsImage = async (file) => {
            // Convert HEIC to JPEG if needed
            if (file.name.toLowerCase().endsWith('.heic') || file.type === 'image/heic') {
                log(`   -> Đang chuyển đổi định dạng HEIC...`);
                try {
                    const blob = await heic2any({
                        blob: file,
                        toType: "image/jpeg",
                        quality: 0.8
                    });
                    // heic2any can return an array of blobs if it's an image sequence, just take the first
                    file = Array.isArray(blob) ? blob[0] : blob;
                } catch (e) {
                    throw new Error(`Lỗi chuyển đổi HEIC: ${e.message}`);
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

        // Create a hidden canvas for image processing
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });

        // Process images sequentially to avoid locking up browser UI
        for (let i = 0; i < total; i++) {
            const file = files[i];
            log(`[${i+1}/${total}] Đang đọc: ${file.name}`);
            
            try {
                const img = await readFileAsImage(file);
                
                // Set canvas size and draw image
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0, img.width, img.height);
                
                const imageData = ctx.getImageData(0, 0, img.width, img.height);
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });

                if (code) {
                    log(`-> Tìm thấy mã QR.`);
                    results.push({
                        filename: file.name,
                        qrData: code.data,
                        error: null,
                        fromOCR: false
                    });
                } else {
                    log(`-> Không đọc được QR, đang thử quét OCR...`);
                    try {
                        const { data: { text } } = await Tesseract.recognize(img, 'vie');
                        let ocrData = {
                            'CCCD': '', 'CMND': '', 'Họ tên': '', 'Ngày sinh': '',
                            'Giới tính': '', 'Nơi thường trú gốc': '', 'Ngày cấp CCCD': ''
                        };
                        
                        // Parse OCR text using RegExp
                        const cccdMatch = text.match(/\b\d{12}\b/);
                        if (cccdMatch) ocrData['CCCD'] = cccdMatch[0];
                        
                        const dates = text.match(/\b\d{2}\/\d{2}\/\d{4}\b/g);
                        if (dates && dates.length >= 1) ocrData['Ngày sinh'] = dates[0];
                        if (dates && dates.length >= 2) ocrData['Ngày cấp CCCD'] = dates[1];
                        
                        if (/\bNam\b/i.test(text)) {
                            ocrData['Giới tính'] = 'Nam';
                        } else if (/\bN[uưứữ][\s]*\b/i.test(text) || /\bNữ\b/i.test(text)) {
                            ocrData['Giới tính'] = 'Nữ';
                        }
                        
                        const lines = text.split('\n').map(l => l.trim()).filter(l => l);
                        for (let j = 0; j < lines.length; j++) {
                            const line = lines[j];
                            if (line.includes("Họ và tên") || line.includes("Họ chữ đệm") || line.includes("Full name")) {
                                if (line.includes(":")) {
                                    let namePart = line.split(":")[1].trim();
                                    if (namePart === namePart.toUpperCase() && namePart.length > 3) {
                                        ocrData['Họ tên'] = namePart;
                                        break;
                                    }
                                }
                                if (j + 1 < lines.length) {
                                    let nextLine = lines[j+1].replace(/\|/g, '').trim();
                                    if (nextLine === nextLine.toUpperCase() && nextLine.length > 3) {
                                        ocrData['Họ tên'] = nextLine;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        results.push({
                            filename: file.name,
                            qrData: null,
                            ocrData: ocrData,
                            error: null,
                            fromOCR: true
                        });
                    } catch (ocrErr) {
                        log(`-> Lỗi quét OCR: ${ocrErr.message}`);
                        results.push({
                            filename: file.name,
                            qrData: null,
                            error: "Lỗi quét OCR",
                            fromOCR: false
                        });
                    }
                }
            } catch (err) {
                log(`-> Lỗi đọc file: ${err.message}`);
                results.push({
                    filename: file.name,
                    qrData: null,
                    error: "Lỗi xử lý ảnh",
                    fromOCR: false
                });
            }

            processedCount++;
            progressText.textContent = `${processedCount}/${total}`;
            progressFill.style.width = `${(processedCount / total) * 100}%`;
        }

        log(`Hoàn tất đọc ${total} file. Chuẩn bị gửi lên server...`);
        sendToServer(results);
    });

    async function sendToServer(results) {
        serverSection.classList.remove('hidden');
        serverStatusText.textContent = 'Đang gửi dữ liệu lên server xử lý API chuẩn hóa và tạo Excel...';
        
        try {
            const response = await fetch('process.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ data: results })
            });

            const resData = await response.json();
            
            if (resData.success) {
                serverStatusText.textContent = 'Xử lý thành công!';
                downloadArea.classList.remove('hidden');
                downloadLink.href = resData.downloadUrl;
            } else {
                serverStatusText.textContent = `Lỗi server: ${resData.message}`;
            }
        } catch (error) {
            serverStatusText.textContent = `Lỗi kết nối: ${error.message}`;
        }
    }
});
