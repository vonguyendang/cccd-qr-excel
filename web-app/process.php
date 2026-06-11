<?php
// Tăng giới hạn memory và execution time nếu file quá lớn
ini_set('memory_limit', '512M');
set_time_limit(300);

require 'vendor/autoload.php';

use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Font;

header('Content-Type: application/json');

$json = file_get_contents('php://input');
$requestData = json_decode($json, true);

// Handle python AI QR scanning via AJAX
if (isset($_GET['action']) && $_GET['action'] === 'scan_qr') {
    if (!isset($requestData['imageBase64'])) {
        echo json_encode(['success' => false, 'error' => 'No image data']);
        exit;
    }
    
    // Convert base64 to temp image
    $base64 = $requestData['imageBase64'];
    $parts = explode(',', $base64);
    $data = isset($parts[1]) ? base64_decode($parts[1]) : base64_decode($base64);
    
    $tmpFilePath = sys_get_temp_dir() . '/' . uniqid('cccd_') . '.jpg';
    file_put_contents($tmpFilePath, $data);
    
    // Execute python script
    $pythonCmd = escapeshellarg(__DIR__ . '/../python-app/venv/bin/python');
    $scriptPath = escapeshellarg(__DIR__ . '/../python-app/scan.py');
    $imgArg = escapeshellarg($tmpFilePath);
    
    $output = shell_exec("$pythonCmd $scriptPath $imgArg 2>&1");
    unlink($tmpFilePath);
    
    // Check output
    $decoded = json_decode($output, true);
    if (is_array($decoded)) {
        echo json_encode($decoded);
    } else {
        echo json_encode(['success' => false, 'error' => 'Python execution error', 'raw' => $output]);
    }
    exit;
}

if (!isset($requestData['data']) || !is_array($requestData['data'])) {
    echo json_encode(['success' => false, 'message' => 'Dữ liệu không hợp lệ']);
    exit;
}

$items = $requestData['data'];

// URL API Chuẩn hóa
$apiUrl = getenv('ADDRESS_API_URL') ?: 'https://diachi.io/api/convert-batch';

function formatDate(string $dateStr = ''): string {
    if (!$dateStr || strlen($dateStr) !== 8) return $dateStr;
    return substr($dateStr, 0, 2) . '/' . substr($dateStr, 2, 2) . '/' . substr($dateStr, 4, 4);
}

function processQRString(string $qrString): array {
    $parts = explode('|', $qrString);
    $data = [
        'CCCD' => $parts[0] ?? '',
        'CMND' => $parts[1] ?? '',
        'Họ tên' => $parts[2] ?? '',
        'Ngày sinh' => isset($parts[3]) ? formatDate($parts[3]) : '',
        'Giới tính' => $parts[4] ?? '',
        'Nơi thường trú gốc' => $parts[5] ?? '',
        'Ngày cấp CCCD' => isset($parts[6]) ? formatDate($parts[6]) : '',
    ];

    $notes = [];
    if (empty($data['Ngày cấp CCCD'])) $notes[] = 'Thiếu ngày cấp';
    if (empty($data['Nơi thường trú gốc'])) $notes[] = 'Thiếu nơi thường trú';

    return [$data, $notes];
}

function callAddressAPI(array $addressList, string $apiUrl): array {
    if (empty($addressList)) return [];

    $mh = curl_multi_init();
    $curlArray = [];
    
    $headers = [
        'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) Gecko/20100101 Firefox/151.0',
        'Accept: application/json, text/plain, */*',
        'Content-Type: application/json',
        'x-kas: 89232422',
        'Origin: https://tienich.vnhub.com',
        'Referer: https://tienich.vnhub.com/'
    ];

    foreach ($addressList as $i => $addr) {
        $ch = curl_init('https://tienich.vnhub.com/api/wards');
        $payload = json_encode(['address' => $addr]);
        
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        
        $curlArray[$i] = $ch;
        curl_multi_add_handle($mh, $ch);
    }
    
    // Execute all queries simultaneously
    $running = null;
    do {
        curl_multi_exec($mh, $running);
        curl_multi_select($mh);
    } while ($running > 0);
    
    $results = [];
    foreach ($addressList as $i => $addr) {
        $response = curl_multi_getcontent($curlArray[$i]);
        $error = curl_error($curlArray[$i]);
        curl_multi_remove_handle($mh, $curlArray[$i]);
        
        if ($error || !$response) {
            $results[] = ["original" => $addr, "success" => false, "error" => "Lỗi kết nối API: " . ($error ? $error : "Empty response")];
        } else {
            $resData = json_decode($response, true);
            if (isset($resData['success']) && $resData['success'] === true && !empty($resData['data'][0]['address'])) {
                $converted = $resData['data'][0]['address'];
                $results[] = [
                    "original" => $addr, 
                    "success" => true, 
                    "converted" => $converted
                ];
            } else {
                $results[] = ["original" => $addr, "success" => false, "error" => "Không tìm thấy địa chỉ tương ứng"];
            }
        }
    }
    
    curl_multi_close($mh);
    return $results;
}

$processedData = [];
$allAddresses = [];
$seenCccds = [];

foreach ($items as $idx => $item) {
    $rowData = [
        'Họ tên' => '', 'CCCD' => '', 'CMND' => '', 'Giới tính' => '',
        'Ngày sinh' => '', 'Nơi thường trú gốc' => '', 'Địa chỉ chuẩn hóa mới' => '',
        'Ngày cấp CCCD' => '', 'Ghi chú' => '', 'QR Raw' => ''
    ];
    $notes = [];

    if (!empty($item['error'])) {
        $notes[] = $item['error'];
    } else if (!empty($item['qrData'])) {
        $rowData['QR Raw'] = $item['qrData'];
        list($extracted, $validationNotes) = processQRString($item['qrData']);
        
        // Deduplication logic
        $cccdNum = $extracted['CCCD'] ?? '';
        if ($cccdNum !== '') {
            if (isset($seenCccds[$cccdNum])) {
                continue; // Bỏ qua dữ liệu trùng lặp
            }
            $seenCccds[$cccdNum] = true;
        }

        $rowData = array_merge($rowData, $extracted);
        $notes = array_merge($notes, $validationNotes);
    } else if (!empty($item['fromOCR']) && $item['fromOCR'] === true && !empty($item['ocrData'])) {
        $extracted = $item['ocrData'];
        $notes[] = "Lấy bằng OCR";
        
        // Deduplication logic for OCR
        $cccdNum = $extracted['CCCD'] ?? '';
        if ($cccdNum !== '') {
            if (isset($seenCccds[$cccdNum])) {
                continue; // Bỏ qua dữ liệu trùng lặp
            }
            $seenCccds[$cccdNum] = true;
        }

        $rowData = array_merge($rowData, $extracted);
    }

    $rowData['Ghi chú'] = implode('; ', $notes);
    $processedData[$idx] = $rowData; // maintain order
}

// Lấy danh sách địa chỉ duy nhất để chuẩn hóa
$uniqueAddresses = [];
foreach ($processedData as $row) {
    if (!empty($row['Nơi thường trú gốc'])) {
        $uniqueAddresses[$row['Nơi thường trú gốc']] = true;
    }
}
$uniqueAddresses = array_keys($uniqueAddresses);
$addressMap = [];

// Batch address processing (chunks of 100)
$batches = array_chunk($uniqueAddresses, 100);
foreach ($batches as $batch) {
    $apiResults = callAddressAPI($batch, $apiUrl);
    foreach ($apiResults as $j => $result) {
        $addressMap[$batch[$j]] = $result;
    }
}

// Map kết quả API ngược lại vào dữ liệu
foreach ($processedData as &$row) {
    $addr = $row['Nơi thường trú gốc'];
    if (!empty($addr) && isset($addressMap[$addr])) {
        $result = $addressMap[$addr];
        
        $newNotes = [];
        if (!empty($row['Ghi chú'])) {
            $newNotes[] = $row['Ghi chú'];
        }

        if (isset($result['success']) && $result['success']) {
            $row['Địa chỉ chuẩn hóa mới'] = $result['converted'] ?? '';
            if (isset($result['notSure']) && $result['notSure']) {
                $newNotes[] = "Địa chỉ chuyển đổi chưa chắc chắn";
            }
        } else {
            $errMsg = $result['error'] ?? 'Lỗi không xác định khi chuẩn hóa';
            $newNotes[] = $errMsg;
        }

        $row['Ghi chú'] = implode('; ', $newNotes);
    }
}
unset($row); // phá vỡ tham chiếu của foreach

// Export Excel
$spreadsheet = new Spreadsheet();
$sheet = $spreadsheet->getActiveSheet();
$sheet->setTitle('Data');

$headers = [
    "STT", "Họ tên", "CCCD", "CMND", "Giới tính", "Ngày sinh", 
    "Nơi thường trú gốc", "Địa chỉ chuẩn hóa mới", "Ngày cấp CCCD", "Ghi chú", "QR Raw"
];

// Write headers
$colAlpha = 'A';
foreach ($headers as $header) {
    $sheet->setCellValue($colAlpha . '1', $header);
    $sheet->getStyle($colAlpha . '1')->getFont()->setBold(true);
    $colAlpha++;
}

// Write data
$rowNum = 2;
$stt = 1;
foreach ($processedData as $data) {
    $sheet->setCellValue('A' . $rowNum, $stt++);
    $sheet->setCellValue('B' . $rowNum, $data['Họ tên']);
    $sheet->setCellValueExplicit('C' . $rowNum, $data['CCCD'], \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
    $sheet->setCellValueExplicit('D' . $rowNum, $data['CMND'], \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
    $sheet->setCellValue('E' . $rowNum, $data['Giới tính']);
    $sheet->setCellValue('F' . $rowNum, $data['Ngày sinh']);
    $sheet->setCellValue('G' . $rowNum, $data['Nơi thường trú gốc']);
    $sheet->setCellValue('H' . $rowNum, $data['Địa chỉ chuẩn hóa mới']);
    $sheet->setCellValue('I' . $rowNum, $data['Ngày cấp CCCD']);
    $sheet->setCellValue('J' . $rowNum, $data['Ghi chú']);
    $sheet->setCellValue('K' . $rowNum, $data['QR Raw']);
    $rowNum++;
}

// Auto size columns (optional, but good for UX)
foreach (range('A', 'K') as $col) {
    $sheet->getColumnDimension($col)->setAutoSize(true);
}

$timestamp = date('Ymd_His');
$filename = "ket_qua_{$timestamp}.xlsx";
$filepath = __DIR__ . '/exports/' . $filename;

$writer = new Xlsx($spreadsheet);
$writer->save($filepath);

echo json_encode([
    'success' => true,
    'downloadUrl' => 'exports/' . $filename
]);
