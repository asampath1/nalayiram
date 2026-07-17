<?php
/**
 * POC pasuram search: query building, grouping, and HTML rendering.
 * Used by pocindex.php (PasuramsArthamTablePOC).
 */

const POC_SEARCH_TABLE = 'PasuramsArthamTablePOC';

function poc_h(string $text): string
{
    return htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function poc_highlight_terms(string $text, array $searchTerms): string
{
    foreach ($searchTerms as $term) {
        $term = trim((string) $term);
        if ($term === '') {
            continue;
        }
        $highlighted = "<span class='highlight'>" . poc_h($term) . "</span>";
        $text = str_ireplace($term, $highlighted, $text);
    }

    return $text;
}

function poc_alwar_term(string $alwarPrefix): string
{
    $parts = explode('-', $alwarPrefix, 2);
    if (isset($parts[1]) && trim($parts[1]) !== '') {
        return trim($parts[1]);
    }

    return trim($alwarPrefix);
}

/**
 * @return array{
 *     result: mysqli_result|null,
 *     error: string|null,
 *     message: string|null,
 *     searchExecuted: bool,
 *     padhamPrefix: string,
 *     alwarPrefix: string,
 *     divyadesamPrefix: string,
 *     searchTerms: string[]
 * }
 */
function poc_run_search(mysqli $conn, string $method, array $input): array
{
    $defaults = [
        'result' => null,
        'error' => null,
        'message' => null,
        'searchExecuted' => false,
        'padhamPrefix' => '',
        'alwarPrefix' => '',
        'divyadesamPrefix' => '',
        'searchTerms' => [],
    ];

    $padhamPrefix = '';
    $alwarPrefix = '';
    $divyadesamPrefix = '';

    if ($method === 'GET' && isset($input['padhamPrefix'])) {
        $padhamPrefix = trim((string) $input['padhamPrefix']);
        $defaults['searchExecuted'] = true;
    } elseif ($method === 'POST') {
        $padhamPrefix = trim((string) ($input['padhamPrefix'] ?? ''));
        $alwarPrefix = trim((string) ($input['alwarPrefix'] ?? ''));
        $divyadesamPrefix = trim((string) ($input['divyadesamPrefix'] ?? ''));
        $defaults['searchExecuted'] = ($padhamPrefix !== '' || $alwarPrefix !== '' || $divyadesamPrefix !== '');

        if (!$defaults['searchExecuted']) {
            $defaults['message'] = 'Please enter search criteria.';
            return $defaults;
        }
    } else {
        return $defaults;
    }

    $defaults['padhamPrefix'] = $padhamPrefix;
    $defaults['alwarPrefix'] = $alwarPrefix;
    $defaults['divyadesamPrefix'] = $divyadesamPrefix;

    $searchTerms = [];
    if ($padhamPrefix !== '') {
        $searchTerms[] = $padhamPrefix;
    }
    if ($alwarPrefix !== '') {
        $searchTerms[] = poc_alwar_term($alwarPrefix);
    }
    if ($divyadesamPrefix !== '') {
        $searchTerms[] = $divyadesamPrefix;
    }
    $defaults['searchTerms'] = $searchTerms;

    if ($padhamPrefix === 'நித்யாநுஸந்தானம்') {
        $sql = 'SELECT * FROM ' . POC_SEARCH_TABLE . '
                WHERE NithyaanusandhamIndex IS NOT NULL
                ORDER BY NithyaanusandhamIndex, PasuramNumber';
        $result = $conn->query($sql);
        if ($result === false) {
            $defaults['error'] = $conn->error;
            return $defaults;
        }
        $defaults['result'] = $result;
        return $defaults;
    }

    $table = POC_SEARCH_TABLE;
    $conditions = [];
    $types = '';
    $params = [];

    if ($padhamPrefix !== '') {
        if (ctype_digit($padhamPrefix)) {
            $conditions[] = "{$table}.PasuramNumber = ?";
            $types .= 'i';
            $params[] = (int) $padhamPrefix;
        } else {
            $like = '%' . $padhamPrefix . '%';
            $conditions[] = "({$table}.SimilarWords LIKE ? OR {$table}.Pasuram LIKE ?
                OR {$table}.Word LIKE ? OR {$table}.Padham LIKE ?)";
            $types .= 'ssss';
            array_push($params, $like, $like, $like, $like);
        }
    }

    if ($alwarPrefix !== '') {
        $alwarTerm = poc_alwar_term($alwarPrefix);
        if ($alwarTerm !== '') {
            $conditions[] = "{$table}.Alzwar LIKE ?";
            $types .= 's';
            $params[] = '%' . $alwarTerm . '%';
        }
    }

    if ($divyadesamPrefix !== '') {
        $conditions[] = 'DivyaDesamTable.DivyaDesam LIKE ?';
        $types .= 's';
        $params[] = '%' . $divyadesamPrefix . '%';
    }

    if (count($conditions) === 0) {
        return $defaults;
    }

    $sql = "SELECT DISTINCT {$table}.*
            FROM {$table}
            LEFT JOIN DivyaDesamTable
            ON {$table}.PasuramNumber = DivyaDesamTable.PasuramNumber
            WHERE " . implode(' AND ', $conditions) . "
            ORDER BY {$table}.PasuramNumber, {$table}.PattuNumber,
                     {$table}.PadhamNumber, {$table}.Word";

    $result = poc_query_search($conn, $sql, $types, $params);
    if ($result === false) {
        $defaults['error'] = $conn->error;
        return $defaults;
    }

    $defaults['result'] = $result;
    return $defaults;
}

/**
 * Run a search query. Uses prepared statements when available; falls back to
 * escaped query() for hosts without mysqlnd (no mysqli_stmt::get_result).
 *
 * @param array<int, mixed> $params
 * @return mysqli_result|false
 */
function poc_query_search(mysqli $conn, string $sql, string $types, array $params)
{
    if ($types === '') {
        return $conn->query($sql);
    }

    $stmt = $conn->prepare($sql);
    if ($stmt === false) {
        return false;
    }

    $stmt->bind_param($types, ...$params);

    if (!$stmt->execute()) {
        $stmt->close();
        return false;
    }

    if (method_exists($stmt, 'get_result')) {
        $result = $stmt->get_result();
        $stmt->close();
        return $result;
    }

    // Fallback: rebuild SQL with escaped literals (table name is fixed constant).
    $stmt->close();
    return poc_query_search_fallback($conn, $sql, $types, $params);
}

/**
 * @param array<int, mixed> $params
 * @return mysqli_result|false
 */
function poc_query_search_fallback(mysqli $conn, string $sql, string $types, array $params)
{
    $parts = explode('?', $sql);
    if (count($parts) !== count($params) + 1) {
        return false;
    }

    $built = $parts[0];
    for ($i = 0; $i < count($params); $i++) {
        $type = $types[$i] ?? 's';
        if ($type === 'i') {
            $built .= (int) $params[$i];
        } else {
            $built .= "'" . mysqli_real_escape_string($conn, (string) $params[$i]) . "'";
        }
        $built .= $parts[$i + 1];
    }

    return $conn->query($built);
}

function poc_group_results(mysqli_result $result, array $searchTerms): array
{
    $grouped = [];

    while ($row = $result->fetch_assoc()) {
        $pasuramNumber = (int) $row['PasuramNumber'];
        $prabandham = (string) ($row['Prabandham'] ?? '');
        $pattuNumber = $row['PattuNumber'] ?? '';
        $padhamNumber = $row['PadhamNumber'] ?? '';

        $pasuram = poc_highlight_terms(poc_h((string) ($row['Pasuram'] ?? '')), $searchTerms);
        $word = poc_highlight_terms(poc_h((string) ($row['Word'] ?? '')), $searchTerms);
        $meaning = poc_highlight_terms(poc_h((string) ($row['Meaning'] ?? '')), $searchTerms);
        $title = poc_highlight_terms(poc_h((string) ($row['Title'] ?? '')), $searchTerms);

        $word = "<span style='color: red;'>{$word}</span>";
        $meaning = "<span style='color: blue;'>{$meaning}</span>";

        $wordMeaningPair = "{$word} - {$meaning}";
        if ($padhamNumber !== null && $padhamNumber !== '') {
            $wordMeaningPair = "<span style='color: #666;'>" . poc_h((string) $padhamNumber) . '. </span>' . $wordMeaningPair;
        }

        $key = $prabandham . '-' . $pasuramNumber . '-' . $pattuNumber;
        if (!isset($grouped[$key])) {
            $grouped[$key] = [
                'Prabandham' => $prabandham,
                'PasuramNumber' => $pasuramNumber,
                'Pasuram' => $pasuram,
                'PattuNumber' => $pattuNumber,
                'Title' => $title,
                'WordMeaningPairs' => [],
            ];
        }

        $grouped[$key]['WordMeaningPairs'][] = $wordMeaningPair;
    }

    return $grouped;
}

function poc_render_results(array $groupedResults, array $searchTerms, string $pageScript = 'pocindex.php'): void
{
    $resultCount = count($groupedResults);
    $searchTermsString = poc_h(implode(', ', $searchTerms));

    echo "<h2>Search Results for: {$searchTermsString} ({$resultCount} results)</h2>";
    echo "<table id='result-table' style='width:100%'>";
    echo '<tr>
            <th style="width:5%">Pasuram Number</th>
            <th style="width:10%">Prabandham</th>
            <th style="width:35%">Pasuram</th>
            <th style="width:50%">PadhaArtham</th>
          </tr>';

    $rowNumber = 0;
    foreach ($groupedResults as $groupedResult) {
        $rowNumber++;
        $backgroundColor = ($rowNumber % 2 === 0) ? '#f2f2f2' : '#ffffff';

        $pasuramNum = (int) $groupedResult['PasuramNumber'];
        $prabandhamRaw = (string) $groupedResult['Prabandham'];
        $prabandhamEnc = poc_h($prabandhamRaw);

        $pasuramNumberLink = '<a href="' . poc_h($pageScript) . '?padhamPrefix=' . $pasuramNum . '">' . $pasuramNum . '</a>';
        $prabandhamLink = '<a href="' . poc_h($pageScript) . '?padhamPrefix=' . rawurlencode($prabandhamRaw) . '">' . $prabandhamEnc . '</a>';

        $titleDisplay = '';
        $titleRaw = trim(strip_tags((string) ($groupedResult['Title'] ?? '')));
        if ($titleRaw !== '') {
            $titleDisplay = "<span style='color: green;'>{$groupedResult['Title']} </span>";
        }

        $pattuDisplay = '';
        if (isset($groupedResult['PattuNumber']) && $groupedResult['PattuNumber'] !== null && $groupedResult['PattuNumber'] !== '') {
            $pattuDisplay = "<span style='color: red;'>" . poc_h((string) $groupedResult['PattuNumber']) . '</span>';
        }

        echo "<tr class='result-row' data-rowid='{$rowNumber}' style='background-color: {$backgroundColor};'>";
        echo "<td>{$pasuramNumberLink}</td>";
        echo "<td><span style='color: blue;'>{$prabandhamLink}</span>"
            . "<span style='color: rgb(51, 0, 255);'> || </span>{$titleDisplay}{$pattuDisplay}</td>";

        echo '<td><div class="pasuram-column">' . nl2br($groupedResult['Pasuram']) . '</div></td>';

        $wordMeaningColumn = nl2br(implode('<br>', $groupedResult['WordMeaningPairs']));
        echo "<td style='background-color: {$backgroundColor};'>{$wordMeaningColumn}</td>";
        echo '</tr>';
    }

    echo '</table>';
}
