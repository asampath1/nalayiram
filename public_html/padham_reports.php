<?php
/**
 * Padham usage reports (POC only). Reads precomputed JSON.
 * Does not query PasuramsArthamTablePOC.
 */
declare(strict_types=1);

$env = isset($_GET['env']) ? strtolower(trim((string) $_GET['env'])) : 'poc';
if ($env !== 'poc') {
    http_response_code(404);
    header('Content-Type: text/plain; charset=UTF-8');
    echo "Padham reports are POC-only. Open padham_reports.php?env=poc\n";
    exit;
}

$jsonPath = __DIR__ . '/data/padham_reports_poc.json';
$payload = null;
$loadError = '';
if (!is_readable($jsonPath)) {
    $loadError = 'Report JSON missing. Run poc/scripts/build_padham_reports.py --apply';
} else {
    $decoded = json_decode((string) file_get_contents($jsonPath), true);
    if (!is_array($decoded)) {
        $loadError = 'Report JSON could not be parsed.';
    } else {
        $payload = $decoded;
    }
}

$searchScript = 'pocindex.php';
$homeScript = 'pocindex.php';
$releaseNotes = 'newreleasenotespoc.html';

function h(?string $s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8');
}

function search_href(
    string $script,
    string $term,
    string $prabandham = '',
    string $alwar = '',
    bool $exact = false,
    array $stems = [],
    array $blocked = []
): string {
    $term = preg_replace('/\+/', ' ', trim($term)) ?? trim($term);
    $query = ['padhamPrefix' => $term];
    if ($prabandham !== '') {
        $query['prabandhamPrefix'] = $prabandham;
    }
    if ($alwar !== '') {
        $query['alwarPrefix'] = $alwar;
    }
    if ($exact) {
        $query['padhamExact'] = '1';
    }
    $cleanStems = [];
    foreach ($stems as $s) {
        $s = trim((string) $s);
        if ($s !== '') {
            $cleanStems[] = $s;
        }
    }
    $cleanBlocked = [];
    foreach ($blocked as $s) {
        $s = trim((string) $s);
        if ($s !== '') {
            $cleanBlocked[] = $s;
        }
    }
    if ($cleanStems !== []) {
        $query['padhamStems'] = implode(',', $cleanStems);
        $query['padhamIn'] = '1';
    }
    if ($cleanBlocked !== []) {
        $query['padhamNot'] = implode(',', $cleanBlocked);
    }
    return h($script . '?' . http_build_query($query, '', '&', PHP_QUERY_RFC3986));
}

function search_link(
    string $script,
    string $term,
    ?string $label = null,
    string $prabandham = '',
    string $alwar = '',
    bool $exact = false,
    array $stems = [],
    array $blocked = []
): string {
    $label = $label ?? $term;
    return '<a href="' . search_href($script, $term, $prabandham, $alwar, $exact, $stems, $blocked) . '">' . h($label) . '</a>';
}

function html_id(string $prefix, string $name): string
{
    $slug = preg_replace('/\s+/u', '-', trim($name)) ?? trim($name);
    return $prefix . '-' . $slug;
}

function report_colgroup(int $numCols, bool $hasNote, int $extraTextCols = 0): void
{
    echo '<colgroup><col class="term">';
    for ($i = 0; $i < $extraTextCols; $i++) {
        echo '<col class="entity">';
    }
    for ($i = 0; $i < $numCols; $i++) {
        echo '<col class="num">';
    }
    if ($hasNote) {
        echo '<col class="note">';
    }
    echo '</colgroup>';
}

function render_exact_table(
    string $script,
    array $rows,
    bool $showNote = true,
    string $prabandham = '',
    string $alwar = ''
): void {
    $cls = $showNote ? 'has-note' : 'rank-3';
    echo '<div class="table-wrap"><table class="report ' . $cls . '">';
    report_colgroup(2, $showNote);
    echo '<thead><tr><th>பதம்</th><th class="num">வரிகள்</th><th class="num">பாசுரங்கள்</th>';
    if ($showNote) {
        echo '<th>குறிப்பு</th>';
    }
    echo '</tr></thead><tbody>';
    foreach ($rows as $row) {
        $token = (string) ($row['token'] ?? '');
        echo '<tr>';
        echo '<td>' . search_link($script, $token, $token, $prabandham, $alwar, true) . '</td>';
        echo '<td class="num">' . (int) ($row['occ'] ?? 0) . '</td>';
        echo '<td class="num">' . (int) ($row['pasurams'] ?? 0) . '</td>';
        if ($showNote) {
            echo '<td class="note">' . h((string) ($row['note'] ?? '')) . '</td>';
        }
        echo '</tr>';
    }
    echo '</tbody></table></div>';
}

function render_cluster_table(
    string $script,
    array $rows,
    bool $showNote = true,
    string $prabandham = '',
    string $alwar = '',
    bool $showTheme = false
): void {
    $numCols = $showTheme ? 3 : 2;
    $cls = $showTheme ? 'rank-5' : ($showNote ? 'has-note' : 'rank-3');
    echo '<div class="table-wrap"><table class="report ' . $cls . '">';
    report_colgroup($numCols, $showNote);
    echo '<thead><tr><th>பதத் திரட்டு</th>';
    if ($showTheme) {
        echo '<th class="num" title="பதவுரை வரியில் அந்த நாமம்">பத வரிகள்</th>';
        echo '<th class="num" title="பதவுரை வரியில் அந்த நாமம் உள்ள பாசுரங்கள்">பத பாசுரங்கள்</th>';
        echo '<th class="num" title="கருப்பொருள் குறியிட்ட பாசுரங்கள்">கருப்பொருள் பாசுரங்கள்</th>';
    } else {
        echo '<th class="num">வரிகள்</th><th class="num">பாசுரங்கள்</th>';
    }
    if ($showNote) {
        echo '<th>குறிப்பு</th>';
    }
    echo '</tr></thead><tbody>';
    foreach ($rows as $row) {
        $search = (string) ($row['search'] ?? $row['label_ta'] ?? '');
        $label = (string) ($row['label_ta'] ?? $search);
        $stems = is_array($row['stems'] ?? null) ? $row['stems'] : [];
        $blocked = is_array($row['blocked_substrings'] ?? null) ? $row['blocked_substrings'] : [];
        echo '<tr>';
        echo '<td>' . search_link($script, $search, $label, $prabandham, $alwar, false, $stems, $blocked) . '</td>';
        echo '<td class="num">' . (int) ($row['occ'] ?? 0) . '</td>';
        echo '<td class="num">' . (int) ($row['pasurams'] ?? 0) . '</td>';
        if ($showTheme) {
            $themeAlias = (string) ($row['theme_alias'] ?? '');
            echo '<td class="num">';
            if ($themeAlias !== '' && array_key_exists('theme_pasurams', $row)) {
                echo search_link($script, $themeAlias, (string) (int) $row['theme_pasurams']);
            } else {
                echo '—';
            }
            echo '</td>';
        }
        if ($showNote) {
            echo '<td class="note">' . h((string) ($row['note'] ?? '')) . '</td>';
        }
        echo '</tr>';
    }
    echo '</tbody></table></div>';
}

function render_cluster_alwar_matrix(string $script, array $payload): void
{
    $n = count($payload['cross_alwar']['cluster_by_alwar'] ?? []);
    echo '<h3 id="cluster-alwar">பதத் திரட்டு × ஆழ்வார் <span class="meta">(' . $n . ' பதத் திரட்டு)</span></h3>';
    echo '<p>';
    echo '<strong>வாமனன் / நரசிம்மன் / இராமன் / கருடன் / சங்கு / சக்கரம்</strong> — ';
    echo 'கருப்பொருள் குறியிட்ட பாசுர எண்ணிக்கை. ';
    echo 'ஆழி பத வரிகள் வேறு; கருப்பொருள் எண் சக்கரத்துடன் ஒன்று (346). ';
    echo 'மற்ற வரிகள் — பதவுரை வரியில் அந்த நாமம் உள்ள எண்ணிக்கை. ';
    echo '<strong>மொத்தம்</strong> = அந்த வரியின் கூட்டு.';
    echo '</p>';
    $alwarCols = [];
    $firstCluster = $payload['cross_alwar']['cluster_by_alwar'][0] ?? null;
    if (is_array($firstCluster)) {
        foreach ($firstCluster['by_alwar'] ?? [] as $cell) {
            $alwarCols[] = (string) ($cell['alwar'] ?? '');
        }
    }
    echo '<div class="table-wrap"><table class="report matrix">';
    echo '<colgroup><col class="term"><col class="num">';
    foreach ($alwarCols as $_) {
        echo '<col class="num">';
    }
    echo '</colgroup>';
    echo '<thead><tr>';
    echo '<th>பதத் திரட்டு</th>';
    echo '<th class="num">மொத்தம்</th>';
    foreach ($alwarCols as $name) {
        echo '<th class="num">' . h($name) . '</th>';
    }
    echo '</tr></thead><tbody>';
    foreach ($payload['cross_alwar']['cluster_by_alwar'] ?? [] as $cluster) {
        $isTheme = (($cluster['metric'] ?? '') === 'theme_pasurams');
        $themeAlias = (string) ($cluster['theme_alias'] ?? '');
        $clusterLabel = (string) ($cluster['label_ta'] ?? '');
        if ($isTheme && $themeAlias !== '') {
            $nameLink = search_link($script, $themeAlias, $clusterLabel);
        } else {
            $nameLink = search_link(
                $script,
                (string) ($cluster['search'] ?? ''),
                $clusterLabel,
                '',
                '',
                false,
                is_array($cluster['stems'] ?? null) ? $cluster['stems'] : [],
                is_array($cluster['blocked_substrings'] ?? null) ? $cluster['blocked_substrings'] : []
            );
        }
        $total = (int) ($cluster['total'] ?? 0);
        if ($total === 0) {
            foreach ($cluster['by_alwar'] ?? [] as $cell) {
                $total += (int) ($cell['occ'] ?? 0);
            }
        }
        echo '<tr>';
        echo '<td>' . $nameLink . '</td>';
        echo '<td class="num' . ($total === 0 ? ' zero' : '') . '">';
        if ($total > 0 && $isTheme && $themeAlias !== '') {
            echo search_link($script, $themeAlias, (string) $total);
        } else {
            echo $total;
        }
        echo '</td>';
        foreach ($cluster['by_alwar'] ?? [] as $cell) {
            $occ = (int) ($cell['occ'] ?? 0);
            $cellAlwar = (string) ($cell['alwar'] ?? '');
            echo '<td class="num' . ($occ === 0 ? ' zero' : '') . '">';
            if ($occ > 0 && $isTheme && $themeAlias !== '') {
                echo search_link($script, $themeAlias, (string) $occ, '', $cellAlwar);
            } else {
                echo $occ;
            }
            echo '</td>';
        }
        echo '</tr>';
    }
    echo '</tbody></table></div>';
}

$meta = is_array($payload) ? ($payload['meta'] ?? []) : [];
?>
<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>பதவுரை ஆராய்ச்சிகள் — POC</title>
    <link rel="icon" type="image/x-icon" href="Sri.jpg">
    <style>
        html { scroll-behavior: smooth; }
        body {
            font-family: Arial, sans-serif, Helvetica;
            margin: 0;
            padding: 0;
            background: #f4f7fb;
            color: #222;
        }
        header {
            background-color: tomato;
            color: white;
            text-align: center;
            padding: 1em 1em 1.15em;
        }
        header img { width: 180px; height: auto; }
        header h3 { margin: 0.35em 0 0; }
        header h5 { margin: 0.35em 0 0; font-weight: 500; }
        header a { color: white; }
        header .header-meta {
            margin: 0.55em auto 0;
            max-width: 54rem;
            font-size: 0.9rem;
            font-weight: 400;
            line-height: 1.45;
            color: rgba(255, 255, 255, 0.95);
        }
        .container {
            max-width: 1180px;
            margin: 0 auto;
            box-sizing: border-box;
            padding: 0 16px 56px;
        }
        .page-nav {
            position: sticky;
            top: 0;
            z-index: 30;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem 0.7rem;
            margin: 0 -16px 18px;
            padding: 10px 16px;
            background: #fff;
            border-bottom: 1px solid #e4e4e4;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
            font-size: 0.9rem;
        }
        .page-nav a {
            color: #0055aa;
            text-decoration: none;
            padding: 0.28em 0.65em;
            border-radius: 999px;
            background: #f4f8fc;
        }
        .page-nav a:hover { background: #ffe8dc; text-decoration: none; }
        .page-nav label {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            color: #555;
        }
        .page-nav select {
            max-width: 14rem;
            font-size: 0.88rem;
            padding: 0.25em 0.4em;
            border: 1px solid #ccc;
            border-radius: 6px;
            background: #fff;
        }
        .section {
            margin: 0 0 2em;
            scroll-margin-top: 58px;
        }
        .section h2 {
            color: #c0392b;
            font-size: 1.22rem;
            margin: 0 0 0.7em;
            border-bottom: 2px solid tomato;
            padding-bottom: 0.28em;
        }
        .section > p, .note-block {
            color: #333;
            line-height: 1.5;
            font-size: 0.95em;
        }
        .block-card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 14px 14px 8px;
            margin: 0 0 14px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
            scroll-margin-top: 58px;
        }
        .block-card h3 {
            font-size: 1.05rem;
            margin: 0 0 0.4em;
            color: #333;
        }
        .section h3 {
            font-size: 1.02rem;
            margin: 1.1em 0 0.4em;
            color: #333;
        }
        .section h3 .meta,
        .block-card h3 .meta {
            font-weight: 400;
            color: #666;
            margin: 0;
        }
        .block-card h4 {
            margin: 0 0 6px;
            font-size: 0.88rem;
            color: #c0392b;
            font-weight: 600;
        }
        .block-note {
            margin: 0 0 12px;
            padding: 8px 10px;
            background: #fff8f4;
            border-left: 3px solid tomato;
            line-height: 1.45;
            font-size: 0.93em;
        }
        .pair-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 0 0 4px;
        }
        .pair-grid:has(> :only-child) {
            grid-template-columns: 1fr;
        }
        .pair-grid .table-wrap { margin: 0; }
        .table-wrap {
            overflow: auto;
            border: 1px solid #d8d8d8;
            border-radius: 8px;
            background: #fff;
            margin: 0 0 12px;
        }
        table.report {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: 0.92em;
        }
        table.report.rank-3 col.term { width: 50%; }
        table.report.rank-3 col.num { width: 25%; }
        table.report.has-note col.term { width: 22%; }
        table.report.has-note col.num { width: 12%; }
        table.report.has-note col.note { width: auto; }
        table.report.rank-5 col.term { width: 20%; }
        table.report.rank-5 col.num { width: 13%; }
        table.report.rank-5 col.note { width: auto; }
        table.report.rank-4 col.term { width: 28%; }
        table.report.rank-4 col.entity { width: 36%; }
        table.report.rank-4 col.num { width: 18%; }
        table.report.pairs col.term { width: 40%; }
        table.report.pairs col.num { width: 20%; }
        table.report th, table.report td {
            border: 1px solid #e2e2e2;
            padding: 7px 10px;
            vertical-align: top;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        table.report thead th {
            background-color: tomato;
            color: white;
            text-align: left;
            font-weight: 600;
        }
        table.report thead th.num {
            text-align: right;
            white-space: normal;
        }
        table.report td.num {
            text-align: right;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }
        table.report tbody tr:nth-child(even) { background: #f4f8fc; }
        table.report tbody tr:hover td { background: #fff3e8; }
        table.report a { color: #0055aa; text-decoration: none; }
        table.report a:hover { text-decoration: underline; }
        table.report td.note { font-size: 0.9em; color: #444; }
        table.report td.zero { color: #999; }
        table.report.matrix { min-width: 78em; }
        table.report.matrix col.term { width: 9.5em; }
        table.report.matrix col.num { width: 5.1em; }
        table.report.matrix thead th.num {
            font-size: 0.8em;
            line-height: 1.2;
        }
        .error { color: #a00; font-weight: 600; }
        .meta { font-size: 0.88em; color: #555; margin: 0 0 12px; }
        .to-top {
            position: fixed;
            right: 1rem;
            bottom: 1rem;
            z-index: 40;
            background: tomato;
            color: #fff;
            text-decoration: none;
            padding: 0.55em 0.9em;
            border-radius: 999px;
            font-size: 0.86rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
        }
        .to-top:hover { background: #e04b2f; }
        @media (max-width: 800px) {
            .pair-grid { grid-template-columns: 1fr; }
            .page-nav select { max-width: 10rem; }
        }
        @media (max-width: 600px) {
            .container { padding: 0 10px 48px; }
            .page-nav { margin: 0 -10px 14px; padding: 8px 10px; }
            table.report { font-size: 0.84em; }
        }
    </style>
</head>
<body>
    <header>
        <img src="ThirumannKapu.jpeg" alt="திருமண் காப்பு">
        <h3>பதவுரை ஆராய்ச்சிகள் — POC</h3>
        <h5>
            <a href="<?php echo h($homeScript); ?>">← தேடல் முகப்பு</a>
            &nbsp;|&nbsp;
            <a href="bhavam_reports.php?env=poc">பாவம் ஆராய்ச்சி</a>
            &nbsp;|&nbsp;
            <a href="<?php echo h($releaseNotes); ?>" target="_blank">வெளியீட்டு குறிப்புகள்</a>
        </h5>
<?php if (is_array($payload)): ?>
        <p class="header-meta">
            ஆழ்வார் பாசுரங்கள் மட்டும் : <?php echo (int) ($meta['eligible_pasurams'] ?? 0); ?>
            · வரிகள்: <?php echo (int) ($meta['eligible_rows'] ?? 0); ?>
            · தனிப் பதங்கள்: <?php echo (int) ($meta['unique_padhams'] ?? 0); ?>
            · கட்டிய நேரம்: <?php echo h((string) ($meta['built_at'] ?? '')); ?>
        </p>
<?php endif; ?>
    </header>
    <div class="container">
<?php if ($loadError !== ''): ?>
        <p class="error"><?php echo h($loadError); ?></p>
<?php else: ?>
        <nav class="page-nav" aria-label="ஆராய்ச்சிப் பிரிவுகள்">
            <a href="#themes">கருப்பொருள்</a>
            <a href="#corpus">முழு நூல்</a>
            <a href="#cluster-alwar">பதத் திரட்டு × ஆழ்வார்</a>
            <a href="#prabandhams">பிரபந்தம்</a>
            <a href="#alwars">ஆழ்வார்</a>
            <a href="#cross">ஒப்பீடு</a>
            <label>பிரபந்தம்
                <select id="jump-prabandham" aria-label="பிரபந்தம் செல்க">
                    <option value="">செல்க…</option>
<?php foreach ($payload['prabandhams'] ?? [] as $jump):
    $jumpName = (string) ($jump['prabandham'] ?? '');
    if ($jumpName === '') {
        continue;
    }
?>
                    <option value="#<?php echo h(html_id('pb', $jumpName)); ?>"><?php echo h($jumpName); ?></option>
<?php endforeach; ?>
                </select>
            </label>
            <label>ஆழ்வார்
                <select id="jump-alwar" aria-label="ஆழ்வார் செல்க">
                    <option value="">செல்க…</option>
<?php foreach ($payload['alwars'] ?? [] as $jump):
    $jumpName = (string) ($jump['alwar'] ?? '');
    if ($jumpName === '') {
        continue;
    }
?>
                    <option value="#<?php echo h(html_id('az', $jumpName)); ?>"><?php echo h($jumpName); ?></option>
<?php endforeach; ?>
                </select>
            </label>
        </nav>

        <section class="section" id="themes">
            <h2>1. கருப்பொருள் ஆராய்ச்சி</h2>
            <p>
                கருப்பொருள் எண்ணிக்கை = அந்தக் கருப்பொருள் குறியிட்ட <strong>பாசுரங்கள்</strong>
                (ஒரு பாசுரம் குறியிட்டால் அதன் எல்லாப் பத வரிகளிலும் அதே குறி இருக்கும்).
                கீழே உள்ள <strong>பதத் திரட்டு</strong> வேறு: பதவுரை வரியில் அந்த நாமம் இருக்கும் வரிகள் மட்டும்.
                உதாரணம்: வாமனன் பதத் திரட்டு சுமார் 18 வரி; வாமனன் கருப்பொருள் சுமார் 200+ பாசுரம்.
            </p>
            <div class="table-wrap"><table class="report has-note">
                <?php report_colgroup(1, true); ?>
                <thead>
                    <tr>
                        <th>கருப்பொருள்</th>
                        <th class="num">பாசுரங்கள்</th>
                        <th>குறிப்பு</th>
                    </tr>
                </thead>
                <tbody>
<?php foreach ($payload['themes'] ?? [] as $theme):
    $alias = (string) ($theme['search_alias'] ?? $theme['concept'] ?? '');
?>
                    <tr>
                        <td><?php echo search_link($searchScript, $alias, (string) ($theme['concept'] ?? $alias)); ?></td>
                        <td class="num"><?php echo (int) ($theme['tagged_pasurams'] ?? 0); ?></td>
                        <td class="note"><?php echo h((string) ($theme['note'] ?? '')); ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table></div>
<?php foreach ($payload['themes'] ?? [] as $theme):
    $alias = (string) ($theme['search_alias'] ?? $theme['concept'] ?? '');
?>
            <h3><?php echo search_link($searchScript, $alias, (string) ($theme['concept'] ?? $alias)); ?>
                <span class="meta">(<?php echo (int) ($theme['tagged_pasurams'] ?? 0); ?> பாசுரம்)</span>
            </h3>
<?php if (!empty($theme['note'])): ?>
            <p class="block-note"><?php echo h((string) $theme['note']); ?></p>
<?php endif; ?>
            <?php if (!empty($theme['top_padhams'])): ?>
            <p class="meta">இந்தக் கருப்பொருள் பாசுரங்களில் கருப்பொருள் விதை உள்ள பதங்கள் (இடைச்சொல் அல்ல).</p>
            <?php render_exact_table($searchScript, $theme['top_padhams'] ?? [], false); ?>
            <?php else: ?>
            <p>குறியிட்ட பாசுரம் இல்லை.</p>
            <?php endif; ?>
<?php endforeach; ?>

            <h3>ஒரே பாசுரத்தில் சேர்ந்து வரும் பதத் திரட்டுகள்</h3>
            <div class="table-wrap"><table class="report pairs">
                <colgroup><col class="term"><col class="term"><col class="num"></colgroup>
                <thead><tr><th>பதத் திரட்டு</th><th>பதத் திரட்டு</th><th class="num">பாசுரங்கள்</th></tr></thead>
                <tbody>
<?php foreach ($payload['cluster_pairs'] ?? [] as $pair): ?>
                    <tr>
                        <td><?php echo search_link(
                            $searchScript,
                            (string) ($pair['a_label'] ?? ''),
                            (string) ($pair['a_label'] ?? ''),
                            '',
                            '',
                            false,
                            is_array($pair['a_stems'] ?? null) ? $pair['a_stems'] : [],
                            is_array($pair['a_blocked'] ?? null) ? $pair['a_blocked'] : []
                        ); ?></td>
                        <td><?php echo search_link(
                            $searchScript,
                            (string) ($pair['b_label'] ?? ''),
                            (string) ($pair['b_label'] ?? ''),
                            '',
                            '',
                            false,
                            is_array($pair['b_stems'] ?? null) ? $pair['b_stems'] : [],
                            is_array($pair['b_blocked'] ?? null) ? $pair['b_blocked'] : []
                        ); ?></td>
                        <td class="num"><?php echo (int) ($pair['pasurams'] ?? 0); ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table></div>
        </section>

        <section class="section" id="corpus">
            <h2>2. முழு நூல் — அதிகம் வரும் பதங்கள்</h2>
            <h3>அப்படியே உள்ள பதம் (முதல் 50)</h3>
            <p>பதவுரை வரியில் உள்ள சொல் அப்படியே. இடைச்சொற்கள் முதலிடம் பெறுவது இயல்பு.</p>
            <?php render_exact_table($searchScript, $payload['corpus_exact'] ?? []); ?>
            <h3>பொருள் பதத் திரட்டு
                <span class="meta">(<?php echo count($payload['corpus_clusters'] ?? []); ?> பதத் திரட்டு)</span>
            </h3>
            <p>
                நீண்ட அடி முதலில் பொருந்தும். ஒரு வரி ஒரே பதத் திரட்டுக்கு மட்டும்.
                <strong>பத</strong> = பதவுரை வரியில் அந்த நாமம் (வாமனன் = 18).
                <strong>கருப்பொருள்</strong> = குறியிட்ட பாசுரங்கள் (வாமனன் = 216; ஆழி = சக்கரம் = 346).
                பெயர் → பதத் தேடல். கருப்பொருள் எண் → கருப்பொருள் தேடல்.
                <strong>—</strong> = இந்தப் பதத் திரட்டுக்கு கருப்பொருள் இல்லை.
            </p>
            <?php render_cluster_table($searchScript, $payload['corpus_clusters'] ?? [], true, '', '', true); ?>
            <?php render_cluster_alwar_matrix($searchScript, $payload); ?>
        </section>

        <section class="section" id="prabandhams">
            <h2>3. பிரபந்தம் வாரியாக</h2>
<?php foreach ($payload['prabandhams'] ?? [] as $block):
    $pbName = (string) ($block['prabandham'] ?? '');
    $pbAlwar = (string) ($block['alwar'] ?? '');
?>
            <article class="block-card" id="<?php echo h(html_id('pb', $pbName)); ?>">
            <h3><?php echo h($pbName); ?>
                <span class="meta">(<?php echo h($pbAlwar); ?>
                · <?php echo (int) ($block['eligible_pasurams'] ?? 0); ?> பாசுரம்
                · <?php echo (int) ($block['eligible_rows'] ?? 0); ?> வரி)</span>
            </h3>
<?php if (!empty($block['note'])): ?>
            <p class="block-note"><?php echo h((string) $block['note']); ?></p>
<?php endif; ?>
            <div class="pair-grid">
                <div>
                    <h4>அப்படியே உள்ள பதம்</h4>
                    <?php render_exact_table($searchScript, $block['top_exact'] ?? [], false, $pbName, $pbAlwar); ?>
                </div>
<?php if (!empty($block['top_clusters'])): ?>
                <div>
                    <h4>பதத் திரட்டு</h4>
                    <?php render_cluster_table($searchScript, $block['top_clusters'] ?? [], false, $pbName, $pbAlwar); ?>
                </div>
<?php endif; ?>
            </div>
            </article>
<?php endforeach; ?>
        </section>

        <section class="section" id="alwars">
            <h2>4. ஆழ்வார் வாரியாக (12)</h2>
<?php foreach ($payload['alwars'] ?? [] as $block):
    $azName = (string) ($block['alwar'] ?? '');
?>
            <article class="block-card" id="<?php echo h(html_id('az', $azName)); ?>">
            <h3><?php echo h($azName); ?>
                <span class="meta">(<?php echo (int) ($block['eligible_pasurams'] ?? 0); ?> பாசுரம்
                · <?php echo (int) ($block['eligible_rows'] ?? 0); ?> வரி)</span>
            </h3>
<?php if (!empty($block['note'])): ?>
            <p class="block-note"><?php echo h((string) $block['note']); ?></p>
<?php endif; ?>
            <div class="pair-grid">
                <div>
                    <h4>அப்படியே உள்ள பதம்</h4>
                    <?php render_exact_table($searchScript, $block['top_exact'] ?? [], false, '', $azName); ?>
                </div>
                <div>
                    <h4>பதத் திரட்டு</h4>
                    <?php render_cluster_table($searchScript, $block['top_clusters'] ?? [], false, '', $azName); ?>
                </div>
            </div>
            </article>
<?php endforeach; ?>
        </section>

        <section class="section" id="cross">
            <h2>5. ஆழ்வார் / பிரபந்த ஒப்பீடு</h2>
            <p>எண்ணிக்கை <?php echo (int) ($payload['cross_alwar']['min_occ'] ?? 5); ?> அல்லது அதற்கு மேல் உள்ள பதங்கள் மட்டும் (ஒருமுறை வரும் பதங்கள் தவிர).</p>
            <h3>பன்னிரு ஆழ்வாரிலும் உள்ள பதங்கள்</h3>
<?php
$common = $payload['cross_alwar']['common_to_all_alwars'] ?? [];
if ($common === []):
?>
            <p>ஐந்து முறை அல்லது அதற்கு மேல் வரும் ஒரே பதம் பன்னிரு ஆழ்வாரிலும் இல்லை. மதுரகவி (11), திருப்பாண் (10) பாசுரங்கள் குறைவு; இடைச்சொற்களும் எல்லாரிடமும் சேரவில்லை.</p>
<?php else: ?>
            <?php render_exact_table($searchScript, $common, false); ?>
<?php endif; ?>

            <h3>ஒரு ஆழ்வாருக்கு மட்டும் (முதல் 50)</h3>
            <div class="table-wrap"><table class="report rank-4">
                <?php report_colgroup(2, false, 1); ?>
                <thead><tr><th>பதம்</th><th>ஆழ்வார்</th><th class="num">வரிகள்</th><th class="num">பாசுரங்கள்</th></tr></thead>
                <tbody>
<?php foreach ($payload['cross_alwar']['unique_to_one_alwar'] ?? [] as $row): ?>
                    <tr>
                        <td><?php echo search_link($searchScript, (string) ($row['token'] ?? ''), null, '', (string) ($row['alwar'] ?? ''), true); ?></td>
                        <td><?php echo h((string) ($row['alwar'] ?? '')); ?></td>
                        <td class="num"><?php echo (int) ($row['occ'] ?? 0); ?></td>
                        <td class="num"><?php echo (int) ($row['pasurams'] ?? 0); ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table></div>

            <h3>ஒரு பிரபந்தத்துக்கு மட்டும் (முதல் 50)</h3>
            <div class="table-wrap"><table class="report rank-4">
                <?php report_colgroup(2, false, 1); ?>
                <thead><tr><th>பதம்</th><th>பிரபந்தம்</th><th class="num">வரிகள்</th><th class="num">பாசுரங்கள்</th></tr></thead>
                <tbody>
<?php foreach ($payload['cross_alwar']['unique_to_one_prabandham'] ?? [] as $row): ?>
                    <tr>
                        <td><?php echo search_link($searchScript, (string) ($row['token'] ?? ''), null, (string) ($row['prabandham'] ?? ''), '', true); ?></td>
                        <td><?php echo h((string) ($row['prabandham'] ?? '')); ?></td>
                        <td class="num"><?php echo (int) ($row['occ'] ?? 0); ?></td>
                        <td class="num"><?php echo (int) ($row['pasurams'] ?? 0); ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table></div>
        </section>
        <a class="to-top" href="#">மேலே</a>
<?php endif; ?>
    </div>
    <script>
    (function () {
        var pb = document.getElementById('jump-prabandham');
        var az = document.getElementById('jump-alwar');
        if (!pb || !az) {
            return;
        }

        function optionMatch(select, hash) {
            var i;
            for (i = 0; i < select.options.length; i += 1) {
                if (select.options[i].value === hash) {
                    return true;
                }
            }
            return false;
        }

        function syncFromHash() {
            var hash = location.hash || '';
            pb.value = optionMatch(pb, hash) ? hash : '';
            az.value = optionMatch(az, hash) ? hash : '';
        }

        function jumpFrom(select, other) {
            other.value = '';
            if (select.value) {
                location.hash = select.value;
            }
        }

        pb.addEventListener('change', function () { jumpFrom(pb, az); });
        az.addEventListener('change', function () { jumpFrom(az, pb); });
        window.addEventListener('hashchange', syncFromHash);
        syncFromHash();
    })();
    </script>
</body>
</html>
