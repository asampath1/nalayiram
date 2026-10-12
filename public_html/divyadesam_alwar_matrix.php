<?php
include('database.php');

$MATRIX_ENVS = [
    'poc' => [
        'pasuram_table' => 'PasuramsArthamTablePOC',
        'search_script' => 'pocindex.php',
        'home_script' => 'pocindex.php',
        'release_notes' => 'newreleasenotespoc.html',
    ],
    'test' => [
        'pasuram_table' => 'PasuramsArthamTableTest',
        'search_script' => 'test1.php',
        'home_script' => 'test1.php',
        'release_notes' => 'newreleasenotestest.html',
    ],
    'prod' => [
        'pasuram_table' => 'PasuramsArthamTable',
        'search_script' => 'index.php',
        'home_script' => 'index.php',
        'release_notes' => 'newreleasenotes.html',
    ],
];

$env = isset($_GET['env']) ? strtolower(trim($_GET['env'])) : 'poc';
if (!isset($MATRIX_ENVS[$env])) {
    $env = 'poc';
}
$envConfig = $MATRIX_ENVS[$env];
$pasuramTable = $envConfig['pasuram_table'];
$searchScript = $envConfig['search_script'];
$homeScript = $envConfig['home_script'];
$releaseNotes = $envConfig['release_notes'];
?>
<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
<?php if ($env !== 'prod'): ?>
    <meta name="robots" content="noindex, nofollow">
    <link rel="canonical" href="https://nalayiram.in/divyadesam_alwar_matrix.php?env=prod">
<?php else: ?>
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://nalayiram.in/divyadesam_alwar_matrix.php?env=prod">
<?php endif; ?>
    <meta name="description" content="DivyaDesam -- Alwar pasuram count matrix for Nalayira Divya Prabandham.">
    <title>திவ்யதேசம் -- ஆழ்வார் — பாசுர எண்ணிக்கை அட்டவணை</title>
    <link rel="icon" type="image/x-icon" href="Sri.jpg">
    <style>
        body {
            font-family: Arial, sans-serif, Helvetica;
            margin: 0;
            padding: 0;
            background: #f8fcff;
        }

        header {
            background-color: tomato;
            color: white;
            text-align: center;
            padding: 1em;
        }

        header img {
            width: 200px;
            height: auto;
        }

        header h5 {
            margin: 0.35em 0 0;
        }

        header a {
            color: white;
        }

        .container {
            width: 100%;
            box-sizing: border-box;
            padding: 16px 20px 32px;
        }

        .intro {
            margin: 0 0 12px;
            color: #333;
            line-height: 1.45;
        }

        .matrix-wrap {
            overflow: auto;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
            width: 100%;
            max-height: calc(100vh - 220px);
            border: 1px solid #ccc;
            border-radius: 6px;
            background: #fff;
        }

        .matrix-scroll-hint {
            display: none;
            margin: 0 0 8px;
            font-size: 0.88rem;
            color: #666;
        }

        table.matrix {
            border-collapse: separate;
            border-spacing: 0;
            min-width: 100%;
            font-size: 0.92em;
        }

        table.matrix th,
        table.matrix td {
            border: 1px solid #ddd;
            padding: 6px 8px;
            white-space: nowrap;
        }

        table.matrix thead th {
            background-color: tomato;
            color: white;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 3;
        }

        table.matrix thead th.corner {
            left: 0;
            z-index: 4;
            text-align: left;
            min-width: 220px;
        }

        table.matrix thead th.total-col,
        table.matrix tbody td.total-col,
        table.matrix tfoot td.total-col {
            background-color: #ffe8e0;
            font-weight: 700;
        }

        table.matrix thead th.total-col {
            background-color: #d94326;
            color: white;
        }

        table.matrix tbody th {
            position: sticky;
            left: 0;
            z-index: 2;
            background: #fff8f6;
            color: #333;
            text-align: left;
            font-weight: 600;
            min-width: 220px;
            max-width: 280px;
            white-space: normal;
        }

        table.matrix tbody tr.region-row th {
            background: #8b2e1a;
            color: #fff;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
            position: sticky;
            left: 0;
            z-index: 2;
        }

        table.matrix tfoot th {
            position: sticky;
            left: 0;
            bottom: 0;
            z-index: 2;
            background: #ffe8e0;
            text-align: left;
            font-weight: 700;
        }

        table.matrix tfoot td,
        table.matrix tfoot th {
            position: sticky;
            bottom: 0;
            z-index: 2;
            background: #ffe8e0;
            font-weight: 700;
        }

        table.matrix tfoot td.total-col {
            background: #ffd2c2;
            z-index: 3;
        }

        table.matrix td {
            text-align: center;
            min-width: 3.2em;
        }

        .cell-form {
            display: inline;
            margin: 0;
            padding: 0;
        }

        button.cell-link {
            background: none;
            border: none;
            padding: 0;
            margin: 0;
            color: #0066CC;
            font-weight: 600;
            font-size: inherit;
            font-family: inherit;
            text-decoration: underline;
            cursor: pointer;
        }

        button.cell-link:hover {
            color: #004499;
        }

        .error {
            color: #a00;
            font-weight: 600;
        }

        @media (max-width: 700px) {
            header {
                padding: 0.75em;
            }

            header img {
                width: 120px;
            }

            header h3 {
                font-size: 1.05rem;
                line-height: 1.35;
                margin: 0.4em 0;
            }

            .container {
                padding: 10px 10px 24px;
            }

            .intro {
                font-size: 0.9rem;
            }

            .matrix-scroll-hint {
                display: block;
            }

            .matrix-wrap {
                max-height: calc(100vh - 170px);
                border-color: #d94326;
            }

            table.matrix {
                font-size: 0.78em;
            }

            table.matrix th,
            table.matrix td {
                padding: 4px 5px;
            }

            table.matrix thead th.corner,
            table.matrix tbody th {
                min-width: 112px;
                max-width: 132px;
            }
        }
    </style>
</head>
<body>
    <header>
        <img src="ThirumannKapu.jpeg" alt="Header Image">
        <h3>திவ்யதேசம் -- ஆழ்வார் — பாசுர எண்ணிக்கை அட்டவணை</h3>
        <h5><a href="<?php echo htmlspecialchars($homeScript); ?>">← தேடல் முகப்பு</a>
            &nbsp;|&nbsp;
            <a href="<?php echo htmlspecialchars($releaseNotes); ?>" target="_blank">வெளியீட்டு குறிப்புகள்</a>
        </h5>
    </header>
    <div class="container">
        <p class="matrix-scroll-hint">← இடது/வலது நகர்த்தி அனைத்து ஆழ்வார் நெடுவரிசைகளையும் பார்க்கவும் →</p>
<?php

/**
 * POST to environment search page — same path as the main search form (reliable).
 * Grand total (no filters) is plain text, not a link.
 */
function matrix_search_button($count, $alwar = '', $divyadesam = '', $searchScript = 'pocindex.php') {
    if ($count <= 0) {
        return '';
    }
    $count = (int) $count;
    if ($alwar === '' && $divyadesam === '') {
        return (string) $count;
    }
    $html = '<form class="cell-form" method="post" action="'
        . htmlspecialchars($searchScript, ENT_QUOTES, 'UTF-8') . '">';
    if ($alwar !== '') {
        $html .= '<input type="hidden" name="alwarPrefix" value="'
            . htmlspecialchars($alwar, ENT_QUOTES, 'UTF-8') . '">';
    }
    if ($divyadesam !== '') {
        $html .= '<input type="hidden" name="divyadesamPrefix" value="'
            . htmlspecialchars($divyadesam, ENT_QUOTES, 'UTF-8') . '">';
    }
    $html .= '<button type="submit" class="cell-link">' . $count . '</button></form>';
    return $html;
}

/** Display Tamil DivyaDesam label only (strip leading English before comma). */
function divyadesam_tamil_label($divyadesam) {
    $divyadesam = trim($divyadesam);
    $commaPos = strrpos($divyadesam, ',');
    if ($commaPos !== false) {
        $tamil = trim(substr($divyadesam, $commaPos + 1));
        if ($tamil !== '') {
            return $tamil;
        }
    }
    return $divyadesam;
}

/**
 * Canonical Alwar column order (01–12).
 * keys: Alzwar spellings in DB merged into one column.
 * search: prefix passed to pocindex (LIKE match).
 */
$ALWAR_COLUMNS = [
    ['label' => 'பொய்கையாழ்வார்', 'keys' => ['பொய்கையாழ்வார்'], 'search' => 'பொய்கையாழ்வார்'],
    ['label' => 'பூதத்தாழ்வார்', 'keys' => ['பூதத்தாழ்வார்'], 'search' => 'பூதத்தாழ்வார்'],
    ['label' => 'பேயாழ்வார்', 'keys' => ['பேயாழ்வார்'], 'search' => 'பேயாழ்வார்'],
    ['label' => 'திருமழிசையாழ்வார்', 'keys' => ['திருமழிசை ஆழ்வார்', 'திருமழிசையாழ்வார்'], 'search' => 'திருமழிசை'],
    ['label' => 'நம்மாழ்வார்', 'keys' => ['நம்மாழ்வார்'], 'search' => 'நம்மாழ்வார்'],
    ['label' => 'மதுரகவியாழ்வார்', 'keys' => ['மதுரகவியாழ்வார்'], 'search' => 'மதுரகவியாழ்வார்'],
    ['label' => 'குலசேகர ஆழ்வார்', 'keys' => ['குலசேகர ஆழ்வார்', 'குலசேகராழ்வார்'], 'search' => 'குலசேகர'],
    ['label' => 'பெரியாழ்வார்', 'keys' => ['பெரியாழ்வார்'], 'search' => 'பெரியாழ்வார்'],
    ['label' => 'ஆண்டாள்', 'keys' => ['ஆண்டாள்'], 'search' => 'ஆண்டாள்'],
    ['label' => 'தொண்டரடிப்பொடிஆழ்வார்', 'keys' => ['தொண்டரடிப்பொடிஆழ்வார்'], 'search' => 'தொண்டரடிப்பொடி'],
    ['label' => 'திருப்பாண் ஆழ்வார்', 'keys' => ['திருப்பாண் ஆழ்வார்', 'திருப்பாணாழ்வார்'], 'search' => 'திருப்பாண்'],
    ['label' => 'திருமங்கையாழ்வார்', 'keys' => ['திருமங்கையாழ்வார்', 'திருமங்கை ஆழ்வார்'], 'search' => 'திருமங்கை'],
];

function alwar_cell_count(array $matrix, $divyadesam, array $spec) {
    $count = 0;
    foreach ($spec['keys'] as $key) {
        if (isset($matrix[$divyadesam][$key])) {
            $count += (int) $matrix[$divyadesam][$key];
        }
    }
    return $count;
}

function alwar_column_total(array $matrix, array $divyadesams, array $spec) {
    $total = 0;
    foreach ($divyadesams as $divyadesam) {
        $total += alwar_cell_count($matrix, $divyadesam, $spec);
    }
    return $total;
}

$matrixTable = 'DivyaDesamAlwarMatrix';
$useCache = false;
$refreshedAt = '';
$envSql = mysqli_real_escape_string($conn, $env);

$cacheCheck = $conn->query("SHOW TABLES LIKE '{$matrixTable}'");
if ($cacheCheck && $cacheCheck->num_rows > 0) {
    $countResult = $conn->query(
        "SELECT COUNT(*) AS n FROM {$matrixTable} WHERE Environment = '{$envSql}'"
    );
    if ($countResult && ($countRow = $countResult->fetch_assoc()) && (int) $countRow['n'] > 0) {
        $useCache = true;
        $timeResult = $conn->query(
            "SELECT MAX(RefreshedAt) AS refreshed_at FROM {$matrixTable} WHERE Environment = '{$envSql}'"
        );
        if ($timeResult && ($timeRow = $timeResult->fetch_assoc()) && !empty($timeRow['refreshed_at'])) {
            $refreshedAt = $timeRow['refreshed_at'];
        }
    }
}

if ($useCache) {
    $sql = "
        SELECT DivyaDesam, Alzwar, PasuramCount AS pasuram_count
        FROM {$matrixTable}
        WHERE Environment = '{$envSql}'
        ORDER BY DivyaDesam, Alzwar
    ";
} else {
    $sql = "
        SELECT
            d.DivyaDesam,
            p.Alzwar,
            COUNT(DISTINCT p.PasuramNumber) AS pasuram_count
        FROM {$pasuramTable} p
        INNER JOIN DivyaDesamTable d
            ON p.PasuramNumber = d.PasuramNumber
        WHERE p.Alzwar IS NOT NULL AND TRIM(p.Alzwar) <> ''
          AND d.DivyaDesam IS NOT NULL AND TRIM(d.DivyaDesam) <> ''
        GROUP BY d.DivyaDesam, p.Alzwar
        ORDER BY d.DivyaDesam, p.Alzwar
    ";
}
?>
        <p class="intro">
            ஒவ்வொரு கட்டத்திலும் உள்ள எண் = அந்த திவ்யதேசம் + ஆழ்வார் சேர்க்கைக்கான
            <strong>தனித்துவமான பாசுர எண்களின்</strong> எண்ணிக்கை (ஒரு பாசுரத்திற்கு பல பதம் வரிகள்
            ஒன்றாக எண்ணப்படும் — எ.கா. திருவெழுகூற்றிருக்கை 2672, சிறிய திருமடல் 2673).
            எண்ணை அழுத்தினால், தேடல் பக்கத்தில் அந்த ஆழ்வார் மற்றும் திவ்யதேசம் தேர்ந்தெடுக்கப்பட்டது போல் முடிவுகள் திறக்கும்.
            வரிசை / நெடுவரிசை <strong>மொத்தம்</strong> அந்த வரிசை அல்லது ஆழ்வார் மட்டும் தேர்ந்தெடுக்கும்.
<?php if ($refreshedAt !== ''): ?>
            <br><em>கடைசி புதுப்பிப்பு: <?php echo htmlspecialchars($refreshedAt); ?> (முன்கணித்த அட்டவணை)</em>
<?php elseif (!$useCache): ?>
            <br><em>நேரடி கணக்கீடு — விரைவுப் பதிவுக்காக முன்கணித்த அட்டவணையைப் புதுப்பிக்கவும்.</em>
<?php endif; ?>
        </p>
<?php
$result = $conn->query($sql);
if ($result === false) {
    echo '        <p class="error">Query failed: ' . htmlspecialchars($conn->error) . "</p>\n";
    echo "    </div>\n</body>\n</html>\n";
    exit;
}

$matrix = [];
$divyadesams = [];

while ($row = $result->fetch_assoc()) {
    $dd = $row['DivyaDesam'];
    $alwar = $row['Alzwar'];
    $count = (int) $row['pasuram_count'];
    if (!isset($matrix[$dd][$alwar])) {
        $matrix[$dd][$alwar] = 0;
    }
    $matrix[$dd][$alwar] += $count;
    $divyadesams[$dd] = true;
}

$divyadesams = array_keys($divyadesams);
require_once __DIR__ . '/includes/divyadesam_regions_poc.php';
$regionGroups = divyadesam_poc_ordered_groups($divyadesams);
$divyadesams = [];
foreach ($regionGroups as $group) {
    foreach ($group['names'] as $dd) {
        $divyadesams[] = $dd;
    }
}

if (count($divyadesams) === 0) {
    echo "        <p class=\"error\">No DivyaDesam × Alwar data found for {$env}.</p>\n";
    echo "    </div>\n</body>\n</html>\n";
    $conn->close();
    exit;
}

$colTotals = [];
foreach ($ALWAR_COLUMNS as $spec) {
    $colTotals[$spec['label']] = alwar_column_total($matrix, $divyadesams, $spec);
}
$grandTotal = 0;
?>
        <div class="matrix-wrap">
            <table class="matrix">
                <thead>
                    <tr>
                        <th class="corner">திவ்யதேசம் \\ ஆழ்வார்</th>
<?php foreach ($ALWAR_COLUMNS as $spec): ?>
                        <th><?php echo htmlspecialchars($spec['label']); ?></th>
<?php endforeach; ?>
                        <th class="total-col">மொத்தம்</th>
                    </tr>
                </thead>
                <tbody>
<?php
$colspan = count($ALWAR_COLUMNS) + 2;
foreach ($regionGroups as $group) {
    if ($group['names'] === []) {
        continue;
    }
    if ($group['label'] !== '') {
        $heading = $group['label'] . ' (' . (int) $group['count'] . ')';
        echo '                    <tr class="region-row"><th scope="colgroup" colspan="'
            . $colspan . '">' . htmlspecialchars($heading) . "</th></tr>\n";
    }
    foreach ($group['names'] as $dd) {
        $ddLabel = divyadesam_tamil_label($dd);
        echo "                    <tr>\n";
        echo '                        <th scope="row">' . htmlspecialchars($ddLabel) . "</th>\n";
        $rowTotal = 0;
        foreach ($ALWAR_COLUMNS as $spec) {
            $count = alwar_cell_count($matrix, $dd, $spec);
            $rowTotal += $count;
            echo '                        <td>' . matrix_search_button($count, $spec['search'], $ddLabel, $searchScript) . "</td>\n";
        }
        $grandTotal += $rowTotal;
        echo '                        <td class="total-col">' . matrix_search_button($rowTotal, '', $ddLabel, $searchScript) . "</td>\n";
        echo "                    </tr>\n";
    }
}
?>
                </tbody>
                <tfoot>
                    <tr>
                        <th scope="row">மொத்தம்</th>
<?php foreach ($ALWAR_COLUMNS as $spec): ?>
                        <td><?php echo matrix_search_button($colTotals[$spec['label']], $spec['search'], '', $searchScript); ?></td>
<?php endforeach; ?>
                        <td class="total-col"><?php echo matrix_search_button($grandTotal, '', '', $searchScript); ?></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
</body>
</html>
<?php
$conn->close();
?>
