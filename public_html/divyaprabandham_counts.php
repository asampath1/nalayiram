<?php
/**
 * Divya Prabandham completion counts (manual inventory from DivyaPrabandhamCounts).
 *
 * Phase 1: wired from pocindex.php nav. ?env=poc|test|prod (default poc).
 */
declare(strict_types=1);

include __DIR__ . '/database.php';

$ENVS = [
    'poc' => [
        'search_script' => 'pocindex.php',
        'home_script' => 'pocindex.php',
        'release_notes' => 'newreleasenotespoc.html',
    ],
    'test' => [
        'search_script' => 'test1.php',
        'home_script' => 'test1.php',
        'release_notes' => 'newreleasenotestest.html',
    ],
    'prod' => [
        'search_script' => 'index.php',
        'home_script' => 'index.php',
        'release_notes' => 'newreleasenotes.html',
    ],
];

$env = isset($_GET['env']) ? strtolower(trim($_GET['env'])) : 'poc';
if (!isset($ENVS[$env])) {
    $env = 'poc';
}
$envConfig = $ENVS[$env];
$searchScript = $envConfig['search_script'];
$homeScript = $envConfig['home_script'];
$releaseNotes = $envConfig['release_notes'];

$table = 'DivyaPrabandhamCounts';
$rows = [];
$grandTotal = 0;
$updatedAt = '';

$result = $conn->query(
    "SELECT SortOrder, AlwarOrder, Alwar, AlwarSubtotal, DivyaPrabhandham, PadhamPrefix, TotalCount, UpdatedAt
     FROM {$table}
     ORDER BY SortOrder"
);

if ($result === false) {
    $dbError = $conn->error;
} else {
    while ($row = $result->fetch_assoc()) {
        $rows[] = $row;
        $grandTotal += (int) $row['TotalCount'];
        if ($updatedAt === '' && !empty($row['UpdatedAt'])) {
            $updatedAt = $row['UpdatedAt'];
        }
    }
    $result->free();
}

/** @return list<array{start: int, span: int, name: string, subtotal: int}> */
function alwar_rowspans(array $rows): array
{
    $groups = [];
    $n = count($rows);
    $i = 0;
    while ($i < $n) {
        $order = (int) $rows[$i]['AlwarOrder'];
        $start = $i;
        $span = 0;
        while ($i < $n && (int) $rows[$i]['AlwarOrder'] === $order) {
            $span++;
            $i++;
        }
        $groupSum = 0;
        $name = '';
        for ($j = $start; $j < $start + $span; $j++) {
            $groupSum += (int) $rows[$j]['TotalCount'];
            if ($name === '' && !empty($rows[$j]['Alwar'])) {
                $name = $rows[$j]['Alwar'];
            }
        }
        $groups[] = ['start' => $start, 'span' => $span, 'name' => $name, 'subtotal' => $groupSum];
    }
    return $groups;
}

function counts_search_href(string $script, string $prabandhamPrefix, string $alwar): string
{
    // Seed data / release-notes URLs may use '+' between words; search expects spaces.
    $term = preg_replace('/\+/', ' ', trim($prabandhamPrefix));
    $alwarTerm = preg_replace('/\+/', ' ', trim($alwar));
    $href = htmlspecialchars($script, ENT_QUOTES, 'UTF-8')
        . '?prabandhamPrefix='
        . rawurlencode($term);
    if ($alwarTerm !== '') {
        $href .= '&alwarPrefix=' . rawurlencode($alwarTerm);
    }
    return $href;
}

$rowspans = alwar_rowspans($rows);
$spanByStart = [];
$alwarByRow = [];
foreach ($rowspans as $g) {
    $spanByStart[$g['start']] = $g;
    for ($j = $g['start']; $j < $g['start'] + $g['span']; $j++) {
        $alwarByRow[$j] = $g['name'];
    }
}

function counts_stripe_class(int $alwarOrder): string
{
    return ($alwarOrder % 2 === 0) ? 'stripe-even' : 'stripe-odd';
}
?>
<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Divya Prabandham completion counts for Nalayira Divya Prabandham.">
    <title>திவ்யப்ரபந்தம் — எண்ணிக்கை</title>
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
            max-width: 880px;
            margin: 0 auto;
            box-sizing: border-box;
            padding: 16px 16px 32px;
        }

        .intro {
            margin: 0 0 14px;
            color: #333;
            line-height: 1.5;
            font-size: 0.95em;
        }

        .counts-wrap {
            overflow: auto;
            border: 1px solid #d4d4d4;
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
        }

        table.counts {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.96em;
            table-layout: fixed;
        }

        table.counts col.col-alwar {
            width: 34%;
        }

        table.counts col.col-prabandham {
            width: 48%;
        }

        table.counts col.col-count {
            width: 18%;
        }

        table.counts th,
        table.counts td {
            border: 1px solid #e2e2e2;
            padding: 10px 12px;
            vertical-align: middle;
            line-height: 1.35;
        }

        table.counts thead th {
            background-color: tomato;
            color: white;
            text-align: left;
            font-weight: 600;
        }

        table.counts thead th.num {
            text-align: right;
        }

        table.counts tbody th.alwar-cell {
            font-weight: 600;
            text-align: left;
            border-right: 2px solid #e8cfc9;
        }

        table.counts tbody th.alwar-cell .alwar-subtotal {
            color: #666;
            font-weight: 600;
        }

        table.counts tbody tr.stripe-odd th.alwar-cell,
        table.counts tbody tr.stripe-odd td {
            background: #ffffff;
        }

        table.counts tbody tr.stripe-even th.alwar-cell,
        table.counts tbody tr.stripe-even td {
            background: #f4f8fc;
        }

        table.counts tbody tr:hover td,
        table.counts tbody tr:hover th.alwar-cell {
            background: #fff3e8;
        }

        table.counts td.prabandham {
            word-wrap: break-word;
            overflow-wrap: anywhere;
        }

        table.counts td.num {
            text-align: right;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
            font-weight: 600;
            color: #333;
        }

        table.counts tfoot th,
        table.counts tfoot td {
            background: #ffe8e0;
            font-weight: 700;
            border-top: 2px solid tomato;
        }

        table.counts tfoot td.num {
            color: #c0392b;
            font-size: 1.05em;
        }

        table.counts a {
            color: #0055aa;
            text-decoration: none;
        }

        table.counts a:hover {
            text-decoration: underline;
        }

        @media (max-width: 600px) {
            header img {
                width: 120px;
            }

            header h3 {
                font-size: 1.05rem;
                line-height: 1.35;
            }

            .container {
                padding: 12px 10px 24px;
            }

            .intro {
                font-size: 0.9em;
            }

            table.counts {
                font-size: 0.86em;
                table-layout: auto;
            }

            table.counts th,
            table.counts td {
                padding: 8px 6px;
            }

            table.counts tbody th.alwar-cell,
            table.counts td.prabandham {
                overflow-wrap: anywhere;
                word-break: break-word;
            }

            table.counts col.col-alwar {
                width: 32%;
            }

            table.counts col.col-prabandham {
                width: 48%;
            }

            table.counts col.col-count {
                width: 20%;
            }
        }

        .error {
            color: #a00;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <img src="ThirumannKapu.jpeg" alt="Header Image">
        <h3>திவ்யப்ரபந்தம் — எண்ணிக்கை</h3>
        <h5><a href="<?php echo htmlspecialchars($homeScript); ?>">← தேடல் முகப்பு</a>
            &nbsp;|&nbsp;
            <a href="<?php echo htmlspecialchars($releaseNotes); ?>" target="_blank">வெளியீட்டு குறிப்புகள்</a>
        </h5>
    </header>
    <div class="container">
        <p class="intro">
            இதுவரை ஏற்றப்பட்ட திவ்யப்ரபந்தங்களின் பாசுர எண்ணிக்கை (கைமுறை பதிவு).
            திவ்யப்ரபந்தம் பெயரை அழுத்தினால் தேடல் பக்கத்தில் அந்த பிரபந்தம் திறக்கும்.
<?php if ($updatedAt !== ''): ?>
            <br><em>கடைசி புதுப்பிப்பு: <?php echo htmlspecialchars($updatedAt); ?></em>
<?php endif; ?>
        </p>
<?php if (!empty($dbError)): ?>
        <p class="error">Query failed: <?php echo htmlspecialchars($dbError); ?></p>
        <p class="error">Run seed_divyaprabandham_counts.py --apply or seed_divyaprabandham_counts.php on the server.</p>
<?php elseif (count($rows) === 0): ?>
        <p class="error">No rows in <?php echo htmlspecialchars($table); ?>. Seed the table first.</p>
<?php else: ?>
        <div class="counts-wrap">
            <table class="counts">
                <colgroup>
                    <col class="col-alwar">
                    <col class="col-prabandham">
                    <col class="col-count">
                </colgroup>
                <thead>
                    <tr>
                        <th>ஆழ்வார்</th>
                        <th>திவ்யப்ரபந்தம்</th>
                        <th class="num">எண்ணிக்கை</th>
                    </tr>
                </thead>
                <tbody>
<?php foreach ($rows as $idx => $row): ?>
<?php $stripe = counts_stripe_class((int) $row['AlwarOrder']); ?>
                    <tr class="<?php echo $stripe; ?>">
<?php if (isset($spanByStart[$idx])): ?>
                        <th scope="row" class="alwar-cell <?php echo $stripe; ?>" rowspan="<?php echo (int) $spanByStart[$idx]['span']; ?>">
                            <?php echo htmlspecialchars($spanByStart[$idx]['name']); ?>
                            <span class="alwar-subtotal"> (<?php echo (int) $spanByStart[$idx]['subtotal']; ?>)</span>
                        </th>
<?php endif; ?>
                        <td class="prabandham">
                            <a href="<?php echo counts_search_href($searchScript, $row['PadhamPrefix'], $alwarByRow[$idx] ?? ''); ?>">
                                <?php echo htmlspecialchars($row['DivyaPrabhandham']); ?>
                            </a>
                        </td>
                        <td class="num"><?php echo (int) $row['TotalCount']; ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
                <tfoot>
                    <tr>
                        <th scope="row" colspan="2">மொத்தம் (இதுவரை)</th>
                        <td class="num"><?php echo $grandTotal; ?></td>
                    </tr>
                </tfoot>
            </table>
        </div>
<?php endif; ?>
    </div>
</body>
</html>
<?php
$conn->close();
