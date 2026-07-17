<?php
// api/search.php - Nalayiram.in Official JSON API (Fixed & Working 100%)
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=86400');

include('../database.php'); // உங்கள் database.php path

$response = [
    'success' => false,
    'query' => '',
    'count' => 0,
    'results' => [],
    'execution_time_ms' => 0
];

$start = microtime(true);

try {
    $padhamPrefix = trim($_GET['q'] ?? $_GET['padhamPrefix'] ?? '');
    $limit = min(50, max(1, intval($_GET['limit'] ?? 10)));

    if (empty($padhamPrefix)) {
        echo json_encode(['error' => 'q or padhamPrefix required'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $response['query'] = $padhamPrefix;
    $escaped = mysqli_real_escape_string($conn, $padhamPrefix);

    if ($padhamPrefix === "நித்யாநுஸந்தானம்") {
        $sql = "SELECT * FROM PasuramsArthamTable WHERE NithyaanusandhamIndex IS NOT NULL ORDER BY NithyaanusandhamIndex, PasuramNumber LIMIT $limit";
    } elseif (is_numeric($padhamPrefix)) {
        $sql = "SELECT DISTINCT PasuramsArthamTable.* FROM PasuramsArthamTable LEFT JOIN DivyaDesamTable ON PasuramsArthamTable.PasuramNumber = DivyaDesamTable.PasuramNumber WHERE PasuramsArthamTable.PasuramNumber = '$escaped' ORDER BY PattuNumber, PadhamNumber LIMIT $limit";
    } else {
        $sql = "SELECT DISTINCT PasuramsArthamTable.* FROM PasuramsArthamTable LEFT JOIN DivyaDesamTable ON PasuramsArthamTable.PasuramNumber = DivyaDesamTable.PasuramNumber WHERE (SimilarWords LIKE '%$escaped%' OR Pasuram LIKE '%$escaped%' OR Word LIKE '%$escaped%' OR Padham LIKE '%$escaped%') ORDER BY PasuramNumber, PattuNumber, PadhamNumber LIMIT $limit";
    }

    $result_search = $conn->query($sql);
    if (!$result_search) {
        throw new Exception($conn->error);
    }

    $grouped = [];
    while ($row = $result_search->fetch_assoc()) {
        $key = $row['PasuramNumber'] . '-' . $row['PattuNumber'];
        if (!isset($grouped[$key])) {
            $grouped[$key] = [
                'pasuram_number' => $row['PasuramNumber'],
                'prabandham' => $row['Prabandham'],
                'alzwars' => $row['Alzwars'],
                'pasuram_text' => $row['Pasuram'],
                'title' => $row['Title'] ?? '',
                'pattu_number' => $row['PattuNumber'],
                'words' => []
            ];
        }
        $grouped[$key]['words'][] = [
            'word' => $row['Word'],
            'padham' => $row['Padham'],
            'meaning' => $row['Meaning'],
            'similar_words' => $row['SimilarWords'] ?? ''
        ];
    }

    $response['success'] = true;
    $response['count'] = count($grouped);
    $response['results'] = array_values($grouped);
    $response['execution_time_ms'] = round((microtime(true) - $start) * 1000);

} catch (Exception $e) {
    $response['error'] = $e->getMessage();
}

echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
?>