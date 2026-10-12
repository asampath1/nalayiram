<?php
/**
 * Bhavam research (POC only). Reads precomputed JSON.
 * Tags come from Tableau Pasuram-Nu, not Padham inference.
 */
declare(strict_types=1);

$env = isset($_GET['env']) ? strtolower(trim((string) $_GET['env'])) : 'poc';
if ($env !== 'poc') {
    http_response_code(404);
    header('Content-Type: text/plain; charset=UTF-8');
    echo "Bhavam reports are POC-only. Open bhavam_reports.php?env=poc\n";
    exit;
}

$jsonPath = __DIR__ . '/data/bhavam_reports_poc.json';
$payload = null;
$loadError = '';
if (!is_readable($jsonPath)) {
    $loadError = 'Report JSON missing. Run poc/scripts/build_bhavam_reports.py --apply';
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

function search_href(string $script, string $term): string
{
    $query = ['padhamPrefix' => $term];
    return h($script . '?' . http_build_query($query, '', '&', PHP_QUERY_RFC3986));
}

$meta = is_array($payload) ? ($payload['meta'] ?? []) : [];
$ready = !empty($meta['verse_list_ready']);
?>
<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>பாவம் ஆராய்ச்சி — POC</title>
    <link rel="icon" type="image/x-icon" href="Sri.jpg">
    <style>
        body { font-family: Arial, sans-serif, Helvetica; margin: 0; padding: 0; background: #f4f7fb; color: #222; }
        header { background-color: tomato; color: white; text-align: center; padding: 1em 1em 1.15em; }
        header img { width: 180px; height: auto; }
        header h3 { margin: 0.35em 0 0; }
        header h5 { margin: 0.35em 0 0; font-weight: 500; }
        header a { color: white; }
        header .header-meta { margin: 0.55em auto 0; max-width: 54rem; font-size: 0.9rem; line-height: 1.45; color: rgba(255,255,255,0.95); }
        .container { max-width: 960px; margin: 0 auto; padding: 0 16px 56px; }
        .page-nav { position: sticky; top: 0; z-index: 30; display: flex; flex-wrap: wrap; gap: 0.45rem 0.7rem; margin: 0 -16px 18px; padding: 10px 16px; background: #fff; border-bottom: 1px solid #e4e4e4; box-shadow: 0 2px 10px rgba(0,0,0,0.06); font-size: 0.9rem; }
        .page-nav a { color: #0055aa; text-decoration: none; padding: 0.28em 0.65em; border-radius: 999px; background: #f4f8fc; }
        .page-nav a:hover { background: #ffe8dc; }
        .section { margin: 0 0 2em; }
        .section h2 { color: #c0392b; font-size: 1.22rem; margin: 0 0 0.7em; border-bottom: 2px solid tomato; padding-bottom: 0.28em; }
        .section p { color: #333; line-height: 1.5; font-size: 0.95em; }
        .block-note { margin: 0 0 12px; padding: 8px 10px; background: #fff8f4; border-left: 3px solid tomato; line-height: 1.45; font-size: 0.93em; }
        .table-wrap { overflow: auto; border: 1px solid #d8d8d8; border-radius: 8px; background: #fff; margin: 0 0 12px; }
        table.report { width: 100%; border-collapse: collapse; font-size: 0.92em; }
        table.report th, table.report td { border: 1px solid #e2e2e2; padding: 7px 10px; }
        table.report thead th { background-color: tomato; color: white; text-align: left; }
        table.report td.num, table.report th.num { text-align: right; }
        table.report tbody tr:nth-child(even) { background: #f4f8fc; }
        table.report a { color: #0055aa; text-decoration: none; }
        .error { color: #a00; font-weight: 600; }
        .to-top { position: fixed; right: 1rem; bottom: 1rem; background: tomato; color: #fff; padding: 0.4em 0.75em; border-radius: 999px; text-decoration: none; }
    </style>
</head>
<body>
    <header>
        <img src="ThirumannKapu.jpeg" alt="திருமண் காப்பு">
        <h3>பாவம் ஆராய்ச்சி — POC</h3>
        <h5>
            <a href="<?php echo h($homeScript); ?>">← தேடல் முகப்பு</a>
            &nbsp;|&nbsp;
            <a href="padham_reports.php?env=poc">பதவுரை ஆராய்ச்சிகள்</a>
            &nbsp;|&nbsp;
            <a href="<?php echo h($releaseNotes); ?>" target="_blank">வெளியீட்டு குறிப்புகள்</a>
        </h5>
<?php if (is_array($payload)): ?>
        <p class="header-meta">
            Tableau பாசுரப் பட்டியல்: <?php echo $ready ? ((int) ($meta['csv_pasurams'] ?? 0) . ' பாசுரம்') : 'இல்லை'; ?>
            · கட்டிய நேரம்: <?php echo h((string) ($meta['built_at'] ?? '')); ?>
        </p>
<?php endif; ?>
    </header>
    <div class="container">
<?php if ($loadError !== ''): ?>
        <p class="error"><?php echo h($loadError); ?></p>
<?php else: ?>
        <nav class="page-nav" aria-label="பாவங்கள்">
            <a href="#method">முறை</a>
            <a href="#mother">தாய்</a>
            <a href="#nayaki">நாயகி</a>
            <a href="#thozhi">தோழி</a>
        </nav>

        <section class="section" id="method">
            <h2>ஆசாரியர் பாவம் — பாசுர எண்</h2>
            <p>
                இது பதவுரை ஊகிப்பு அல்ல.
                <a href="https://public.tableau.com/app/profile/ramanuja.dasargal/viz/sd_2/WELCOME" target="_blank" rel="noopener">Ramanuja Dasargal Tableau</a>
                அட்டவணையில் உள்ள <strong>Pasuram-Nu</strong> நம்
                <strong>PasuramNumber</strong> உடன் பொருந்தும் (உதா. 13 = பெரியாழ்வார் 1-1-1).
                அந்த எண்ணுக்கு ஆசாரியர் குறித்த பாவம் (தாய் / நாயகி / தோழி) மட்டும் குறிக்கப்படும்.
                ஆண் (Male) தவிர்க்கப்படும்.
            </p>
<?php if (!empty($payload['blocked']['reason_ta']) && !$ready): ?>
            <p class="block-note"><?php echo h((string) $payload['blocked']['reason_ta']); ?></p>
<?php endif; ?>
        </section>

<?php
$ids = ['Mother' => 'mother', 'Nayaki' => 'nayaki', 'Thozhi' => 'thozhi'];
foreach ($payload['roles'] ?? [] as $block):
    $role = (string) ($block['role'] ?? '');
    $sid = $ids[$role] ?? strtolower($role);
    $alias = (string) ($block['search_alias'] ?? $block['label_ta'] ?? '');
?>
        <section class="section" id="<?php echo h($sid); ?>">
            <h2><?php echo h((string) ($block['label_ta'] ?? $role)); ?></h2>
            <p>
                Tableau வரைபடம் (திசைகாட்டி): <?php echo (int) ($block['compass_total'] ?? 0); ?> பாசுரம்
                · CSV: <?php echo (int) ($block['csv_pasurams'] ?? 0); ?>
                · குறியிட்டது:
                <?php if ($alias !== ''): ?>
                <a href="<?php echo search_href($searchScript, $alias); ?>"><?php echo (int) ($block['db_tagged_pasurams'] ?? 0); ?></a>
                <?php else: ?>
                <?php echo (int) ($block['db_tagged_pasurams'] ?? 0); ?>
                <?php endif; ?>
            </p>
            <div class="table-wrap"><table class="report">
                <thead>
                    <tr>
                        <th>பிரபந்தம்</th>
                        <th class="num">Tableau திசைகாட்டி</th>
                        <th class="num">குறியிட்ட பாசுரங்கள்</th>
                    </tr>
                </thead>
                <tbody>
<?php foreach ($block['prabandhams'] ?? [] as $row): ?>
                    <tr>
                        <td><?php echo h((string) ($row['prabandham'] ?? '')); ?></td>
                        <td class="num"><?php echo (int) ($row['tableau_compass'] ?? 0); ?></td>
                        <td class="num"><?php echo (int) ($row['db_tagged'] ?? 0); ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table></div>
        </section>
<?php endforeach; ?>
        <a class="to-top" href="#">மேலே</a>
<?php endif; ?>
    </div>
</body>
</html>
