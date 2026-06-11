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
    if (empty($apiUrl)) {
        // Mock API
        $results = [];
        foreach ($addressList as $addr) {
            if (strpos($addr, 'Không tìm thấy') !== false) {
                $results[] = ["original" => $addr, "success" => false, "error" => "Không tìm thấy địa chỉ tương ứng trong dữ liệu."];
            } else if (strpos($addr, 'Cũ') !== false) {
                $results[] = ["original" => $addr, "converted" => $addr . " (Mới)", "success" => true, "notSure" => true];
            } else {
                $results[] = ["original" => $addr, "converted" => $addr . " (Đã chuẩn hóa)", "success" => true];
            }
        }
        return $results;
    }

    // Call real API
    $ch = curl_init($apiUrl);
    $payload = json_encode(['addresses' => $addressList]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($payload),
        'Origin: https://diachi.io',
        'Referer: https://diachi.io'
    ]);
    
    $response = curl_exec($ch);
    $error = curl_error($ch);

    if ($error) {
        // fallback on error
        $results = [];
        foreach ($addressList as $addr) {
            $results[] = ["original" => $addr, "success" => false, "error" => "Lỗi API: " . $error];
        }
        return $results;
    }

    $resData = json_decode($response, true);
    return $resData['data'] ?? [];
}

$processedData = [];
$allAddresses = [];
$seenCccds = [];

foreach ($items as $idx => $item) {
    $rowData = [
        'Họ tên' => '', 'CCCD' => '', 'CMND' => '', 'Giới tính' => '',
        'Ngày sinh' => '', 'Nơi thường trú gốc' => '', 'Địa chỉ chuẩn hóa mới' => '',
        'Ngày cấp CCCD' => '', 'Ghi chú' => ''
    ];
    $notes = [];

    if (!empty($item['error'])) {
        $notes[] = $item['error'];
    } else if (!empty($item['qrData'])) {
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
    "Nơi thường trú gốc", "Địa chỉ chuẩn hóa mới", "Ngày cấp CCCD", "Ghi chú"
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
    $rowNum++;
}

// Auto size columns (optional, but good for UX)
foreach (range('A', 'J') as $col) {
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
