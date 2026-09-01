<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <link rel="canonical" href="https://nalayiram.in/">
    <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
    <title>UAT — Nalayira Divya Prabandham Padhavurai Search</title>
    <link rel="icon" type="image/x-icon" href="Sri.jpg">

    <style>
        body {
            font-family: Arial, sans-serif, Helvetica;
            margin: 0; /* Remove default margin */
            padding: 0; /* Remove default padding */
        }

        header {
            background-color: tomato;
            color: white;
            text-align: center;
            padding: 1em 1em 1.15em;
        }

        header img {
            width: 160px;
            height: auto;
            margin-bottom: 0.4em;
        }

        header .site-title {
            margin: 0.2em 0 0.45em;
            padding: 0;
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.35;
            color: white;
        }

        header .site-source {
            margin: 0 auto 0.55em;
            max-width: 52rem;
            font-size: 0.95rem;
            font-weight: 400;
            line-height: 1.45;
            color: rgba(255, 255, 255, 0.95);
        }

        header .search-tips {
            margin: 0 auto;
            max-width: 40rem;
            font-size: 0.85rem;
            font-weight: 400;
            line-height: 1.4;
            color: rgba(255, 255, 255, 0.92);
        }

        header .search-tips a {
            color: white;
            font-weight: 600;
        }

        .site-nav {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.35rem 0.75rem;
            margin: 0.75rem 0 0.25rem;
            padding: 0;
            list-style: none;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .site-nav a {
            white-space: nowrap;
        }

        .site-nav .nav-sep {
            color: #888;
            user-select: none;
        }

        .container {
            width: 100%;
            box-sizing: border-box;
            padding: 12px 20px 20px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1em;
        }

        table, th, td {
            border: 1px solid #ddd;
            border-collapse: collapse;
        }

        th, td {
            padding: 8px;
            text-align: left;
        }

        th {
            background-color: tomato;
            color: white;
            text-align: center;
            vertical-align: middle;
        }

        .group {
            margin-top: 1em;
        }

        .merged-cell {
            text-align: center;
            vertical-align: middle;
        }
        .hidden {
            display: none;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }

        input[type=text] {
            width: 100%;
            padding: 12px 20px;
            margin: 8px 0;
            box-sizing: border-box;
        }

        input[type=submit] {
            background-color: tomato;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }

        .highlight {
            background-color: yellow;
        }

        .even-row {
            background-color: #f2f2f2; /* Light gray color for even rows */
        }

        .odd-row {
            background-color: #ffffff; /* White color for odd rows */
        }

        #result-table {
                  /*  display: none; ---Hide the table initially */
                }

        #search-top {
            scroll-margin-top: 0.5rem;
        }

        .utility-link {
            color: tomato;
            font-size: 0.95rem;
            font-weight: 600;
            text-decoration: none;
            padding: 0.35rem 0.5rem;
            white-space: nowrap;
        }

        .utility-link:hover,
        .utility-link:focus {
            text-decoration: underline;
        }

        .results-toolbar {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.5rem;
            margin: 1rem 0 0.5rem;
        }

        .results-toolbar .results-heading {
            margin: 0;
            flex: 1 1 auto;
        }

        .results-heading {
            font-size: 1.25rem;
            margin: 1rem 0 0.5rem;
            word-break: break-word;
        }

        .results-top-footer {
            display: flex;
            justify-content: flex-end;
            margin: 0.75rem 0 0.25rem;
        }

        .results-wrap {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .pasuram-column {
            white-space: pre-line;
            word-break: break-word;
            line-height: 1.45;
        }

        .padhaartham-details {
            margin: 0;
        }

        .padhaartham-details > summary {
            cursor: pointer;
            font-weight: 600;
            color: #b33;
            list-style: none;
        }

        .padhaartham-details > summary::-webkit-details-marker {
            display: none;
        }

        .ui-autocomplete {
            max-height: 200px;
            overflow-y: auto;
            overflow-x: hidden;
            z-index: 1000;
            background-color: lightblue;
            max-width: min(300px, 92vw);
            box-sizing: border-box;
        }

        .ui-menu-item {
            font-size: 14px;
            line-height: 1.6;
        }

        .form-container {
            display: flex;
            justify-content: stretch;
            align-items: stretch;
            width: 100%;
        }

        .form-inline {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.65rem 1rem;
            width: 100%;
        }

        .form-inline input[type="text"] {
            flex: 1 1 220px;
            min-width: 0;
            max-width: 100%;
            width: auto;
            margin: 0;
        }

        .form-inline .form-joiner {
            flex: 0 0 auto;
            margin: 0;
            padding: 0 0.25rem;
            color: #555;
            font-size: 0.9rem;
        }

        .thaniyan-acharyar {
            font-weight: 700;
            margin: 0 0 0.75rem;
            white-space: pre-line;
            line-height: 1.4;
        }

        .form-inline input[type="submit"] {
            flex: 0 0 auto;
            margin: 0;
        }

        /* Phones / narrow viewports: stack search + card results */
        @media only screen and (max-width: 700px) {
            header img {
                width: 120px;
            }

            header .site-title {
                font-size: 1.1rem;
            }

            header .site-source {
                font-size: 0.85rem;
            }

            .site-nav {
                gap: 0.25rem 0.5rem;
                font-size: 0.88rem;
            }

            .site-nav .nav-sep {
                display: none;
            }

            .container {
                padding: 10px 12px 16px;
            }

            .form-inline {
                flex-direction: column;
                align-items: stretch;
            }

            .form-inline input[type="text"] {
                flex: 1 1 auto;
                width: 100%;
            }

            .form-inline .form-joiner {
                display: none;
            }

            .form-inline input[type="submit"] {
                width: 100%;
            }

            .results-wrap {
                overflow-x: visible;
            }

            #result-table {
                border: 0;
                width: 100%;
            }

            #result-table thead {
                display: none;
            }

            #result-table,
            #result-table tbody,
            #result-table tr,
            #result-table td {
                display: block;
                width: 100%;
                box-sizing: border-box;
                border: 0;
            }

            #result-table tr.result-row {
                margin: 0 0 0.85rem;
                padding: 0.75rem 0.85rem;
                border: 1px solid #ddd;
                border-radius: 8px;
                background: #fff !important;
            }

            #result-table td {
                padding: 0.35rem 0;
            }

            #result-table td::before {
                content: attr(data-label);
                display: block;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                color: #888;
                margin-bottom: 0.15rem;
            }

            #result-table td.col-number {
                display: flex;
                flex-wrap: wrap;
                align-items: baseline;
                gap: 0.35rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid #eee;
                margin-bottom: 0.35rem;
            }

            #result-table td.col-number::before {
                display: inline;
                margin: 0;
            }

            #result-table td.col-padhaartham::before {
                display: none;
            }

            .pasuram-column {
                font-size: 1.05rem;
                line-height: 1.5;
            }

            .padhaartham-details {
                margin-top: 0.25rem;
                padding-top: 0.35rem;
                border-top: 1px solid #eee;
            }

            .padhaartham-body {
                margin-top: 0.45rem;
                max-height: 14rem;
                overflow-y: auto;
                font-size: 0.95rem;
                line-height: 1.45;
                -webkit-overflow-scrolling: touch;
            }
        }

        /* Desktop / wide: meanings always visible (no tap needed) */
        @media only screen and (min-width: 701px) {
            .padhaartham-details > summary {
                display: none;
            }
        }
    </style>
    <!-- jQuery library -->
        <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
        <!-- jQuery UI library for autocomplete -->
        <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
        <script>
            $(document).ready(function(){
                $("#padhamSearch").autocomplete({
                    source: function(request, response) {
                        $.ajax({
                            url: "autocomplete.php",
                            type: "GET",
                            dataType: "json",
                            data: { query: request.term },
                            success: function(data) {
                                // Check if there are suggestions
                                if (data.length > 0) {
                                    response(data); // Display suggestions
                                } else {
                                    response([]); // No suggestions, display nothing
                                }
                            }
                        });
                    },
                    minLength: 2, // Minimum characters before starting search
                    // Optional: format the autocomplete suggestions
                    focus: function( event, ui ) {
                        $( "#padhamSearch" ).val( ui.item.label );
                        return false;
                    },
                    select: function( event, ui ) {
                        $( "#padhamSearch" ).val( ui.item.label );
                        return false;
                    }
                }).data("ui-autocomplete")._renderMenu = function(ul, items) {
                    var self = this;
                    $.each(items, function(index, item) {
                        self._renderItemData(ul, item);
                    });
                };
            });
    </script>

<script>
            $(document).ready(function(){
                $("#alzwarSearch").autocomplete({
                    source: function(request, response) {
                        $.ajax({
                            url: "alzwarautocomplete.php",
                            type: "GET",
                            dataType: "json",
                            data: { query: request.term },
                            success: function(data) {
                                // Check if there are suggestions
                                if (data.length > 0) {
                                    response(data); // Display suggestions
                                } else {
                                    response([]); // No suggestions, display nothing
                                }
                            }
                        });
                    },
                    minLength: 2, // Minimum characters before starting search
                    // Optional: format the autocomplete suggestions
                    focus: function( event, ui ) {
                        $( "#alzwarSearch" ).val( ui.item.label );
                        return false;
                    },
                    select: function( event, ui ) {
                        $( "#alzwarSearch" ).val( ui.item.label );
                        return false;
                    }
                }).data("ui-autocomplete")._renderMenu = function(ul, items) {
                    var self = this;
                    $.each(items, function(index, item) {
                        self._renderItemData(ul, item);
                    });
                };
            });
    </script>

    <script>
            $(document).ready(function(){
                $("#divyadesamSearch").autocomplete({
                    source: function(request, response) {
                        $.ajax({
                            url: "divyadesamautocomplete.php",
                            type: "GET",
                            dataType: "json",
                            data: { query: request.term, env: "test" },
                            success: function(data) {
                                // Check if there are suggestions
                                if (data.length > 0) {
                                    response(data); // Display suggestions
                                } else {
                                    response([]); // No suggestions, display nothing
                                }
                            }
                        });
                    },
                    minLength: 2, // Minimum characters before starting search
                    // Optional: format the autocomplete suggestions
                    focus: function( event, ui ) {
                        $( "#divyadesamSearch" ).val( ui.item.label );
                        return false;
                    },
                    select: function( event, ui ) {
                        $( "#divyadesamSearch" ).val( ui.item.label );
                        return false;
                    }
                }).data("ui-autocomplete")._renderMenu = function(ul, items) {
                    var self = this;
                    $.each(items, function(index, item) {
                        self._renderItemData(ul, item);
                    });
                };
            });
    </script>




</head>
<body>
     <header>
        <img src="ThirumannKapu.jpeg" alt="திருமண் காப்பு">
        <h1 class="site-title">ஆழ்வார்கள் அருளிச்செய்த நாலாயிர திவ்யப் பிரபந்தம் - பதவுரை தேடல்</h1>
        <p class="site-source">திவ்யார்த்த தீபிகை (ஸ்ரீ காஞ்சி பிரதிவாதி பயங்கரம் அண்ணங்கராசாரியார்) · சில தொகுப்புகளில் பெரியவாச்சான் பிள்ளை, நம்பிள்ளை, ஸ்ரீ மணவாள மாமுனிகள் அவதாரிகை</p>
        <p class="search-tips">உதாரணம்: திருப்பாவை, vamanan, 940, 2-8-2, 1-1 வாடினேன் வாடி</p>
        <p class="search-tips"><a href="mailto:feedback@nalayiram.in">கருத்து: feedback@nalayiram.in</a></p>
    </header>
            <div class="container">
                    <div id="search-top" tabindex="-1">
                    <nav class="site-nav" aria-label="முதன்மை வழிசெலுத்தல்">
                        <a href="https://nalayiram.in/test1.php?padhamPrefix=Thaniyan" class="customSubmit">தனியன்கள்</a>
                        <span class="nav-sep">|</span>
                        <a href="https://nalayiram.in/test1.php?padhamPrefix=நித்யாநுஸந்தானம்" class="customSubmit">நித்யாநுஸந்தானம்</a>
                        <span class="nav-sep">|</span>
                        <a href="https://nalayiram.in/test1.php?padhamPrefix=சாற்றுமுறை" class="customSubmit">சாற்றுமுறை</a>
                        <span class="nav-sep">|</span>
                        <a href="divyaprabandham_counts.php?env=test" class="customSubmit">திவ்யப்ரபந்தம்-எண்ணிக்கை</a>
                        <span class="nav-sep">|</span>
                        <a href="newreleasenotestest.html" class="customSubmit">நாலாயிர திவ்யப்ரபந்தப் பாசுரங்களின் அடைவு</a>
                        <span class="nav-sep">|</span>
                        <a href="divyadesam_alwar_matrix.php?env=test" class="customSubmit">திவ்யதேசம் -ஆழ்வார் -பாசுர எண்ணிக்கை அட்டவணை</a>
                        <span class="nav-sep">|</span>
                        <a href="help.html?env=test" class="customSubmit">தேடல் உதவி</a>
                    </nav>
  
<?php
// Prefill form fields from GET/POST (matrix links use GET).
function normalize_search_term(string $term): string
{
    return preg_replace('/\+/', ' ', trim($term));
}

$formPadham = '';
$formAlwar = '';
$formDivyadesam = '';
if ($_SERVER["REQUEST_METHOD"] == "GET") {
    if (isset($_GET['prabandhamPrefix'])) {
        $formPadham = htmlspecialchars(normalize_search_term($_GET['prabandhamPrefix']), ENT_QUOTES, 'UTF-8');
    } else {
        $formPadham = isset($_GET['padhamPrefix']) ? htmlspecialchars(normalize_search_term($_GET['padhamPrefix']), ENT_QUOTES, 'UTF-8') : '';
    }
    $formAlwar = isset($_GET['alwarPrefix']) ? htmlspecialchars(normalize_search_term($_GET['alwarPrefix']), ENT_QUOTES, 'UTF-8') : '';
    $formDivyadesam = isset($_GET['divyadesamPrefix']) ? htmlspecialchars(normalize_search_term($_GET['divyadesamPrefix']), ENT_QUOTES, 'UTF-8') : '';
} elseif ($_SERVER["REQUEST_METHOD"] == "POST") {
    $formPadham = isset($_POST['padhamPrefix']) ? htmlspecialchars(normalize_search_term($_POST['padhamPrefix']), ENT_QUOTES, 'UTF-8') : '';
    $formAlwar = isset($_POST['alwarPrefix']) ? htmlspecialchars(normalize_search_term($_POST['alwarPrefix']), ENT_QUOTES, 'UTF-8') : '';
    $formDivyadesam = isset($_POST['divyadesamPrefix']) ? htmlspecialchars(normalize_search_term($_POST['divyadesamPrefix']), ENT_QUOTES, 'UTF-8') : '';
}
?>
                    <div class="form-container">
                        <form class="form-inline" id="searchForm" action="" method="post">
                            <input type="text" id="padhamSearch" name="padhamPrefix" value="<?php echo $formPadham; ?>" placeholder="Padham / word / number — மணிவண்ணா, 2-8-2, 940">
                             <span class="form-joiner">and/or</span>
                            <input type="text" id="alzwarSearch" name="alwarPrefix" value="<?php echo $formAlwar; ?>" placeholder="Alwar — Tamil or English">
                             <span class="form-joiner">and/or</span>
                            <input type="text" id="divyadesamSearch" name="divyadesamPrefix" value="<?php echo $formDivyadesam; ?>" placeholder="Divyadesam — Tamil or English">
                            <input type="submit" value="Search">
                            <a href="test1.php" class="utility-link" id="clearSearch" aria-label="Clear all search fields">Clear</a>
                        </form>
                    </div>
                    </div>

<?php
include('database.php'); 

$searchType = '';
$selectedPrefix = '';
$padhamPrefix = '';
$prabandhamPrefix = '';
$alwarPrefix = '';
$divyadesamPrefix = '';
$sql_search = '';
$result_search = null;

/**
 * Autocomplete English labels → DB Alzwar (Tamil). Used when the second box
 * has only "Nammalwar" instead of "Nammalwar-நம்மாழ்வார்".
 */
function poc_alwar_english_to_tamil($term) {
    static $map = [
        'nammalwar' => 'நம்மாழ்வார்',
        'madhurakavi alwar' => 'மதுரகவியாழ்வார்',
        'periyalwar' => 'பெரியாழ்வார்',
        'andal' => 'ஆண்டாள்',
        'thondaradpipodi alwar' => 'தொண்டரடிப்பொடிஆழ்வார்',
        'thiruppan alwar' => 'திருப்பாண் ஆழ்வார்',
        'thirumangai alwar' => 'திருமங்கையாழ்வார்',
        'poigai alwar' => 'பொய்கையாழ்வார்',
        'boothathalwar' => 'பூதத்தாழ்வார்',
        'peyalwar' => 'பேயாழ்வார்',
        'thirumazhisai alwar' => 'திருமழிசையாழ்வார்',
        'kulasekara alwar' => 'குலசேகர ஆழ்வார்',
        'nadamuni' => 'நாதமுனி',
    ];
    $key = strtolower(trim($term));
    return $map[$key] ?? $term;
}

/**
 * Build Alzwar LIKE condition.
 * Autocomplete uses "English-Tamil"; matrix links pass plain Alzwar from DB.
 */
function poc_alwar_condition($alwarPrefix) {
    if ($alwarPrefix === '') {
        return null;
    }
    $parts = explode("-", $alwarPrefix, 2);
    if (isset($parts[1]) && trim($parts[1]) !== '') {
        $alwarPrefix = trim($parts[1]);
    } else {
        $alwarPrefix = trim($alwarPrefix);
        $alwarPrefix = poc_alwar_english_to_tamil($alwarPrefix);
    }
    if ($alwarPrefix === '') {
        return null;
    }
    return "Alzwar LIKE '%$alwarPrefix%'";
}

function poc_text_search_condition($term) {
    return "(SimilarWords LIKE '%$term%' OR Pasuram LIKE '%$term%' OR Prabandham LIKE '%$term%' OR Word LIKE '%$term%' OR Meaning LIKE '%$term%')";
}

/** 3.1.1 / 3-1-1 / 3 1 1 — verse codes, not a decimal pasuram number. */
function poc_is_pathigam_code($term) {
    return (bool) preg_match('/^\d+(?:[.\-\s]+\d+)+$/', $term);
}

function poc_pathigam_code_variants($term) {
    $parts = preg_split('/[.\-\s]+/', trim($term), -1, PREG_SPLIT_NO_EMPTY);
    if (count($parts) < 2) {
        return [$term];
    }
    foreach ($parts as $part) {
        if (!ctype_digit($part)) {
            return [$term];
        }
    }
    return array_values(array_unique([
        implode('.', $parts),
        implode('-', $parts),
        implode(' ', $parts),
        $term,
    ]));
}

/** Literal pathigam code for MySQL REGEXP (`\.` is not portable; `[.]` is). */
function poc_mysql_regexp_escape($term) {
    $out = '';
    $len = strlen($term);
    for ($i = 0; $i < $len; $i++) {
        $ch = $term[$i];
        if ($ch === '.') {
            $out .= '[.]';
        } elseif ($ch === '-') {
            $out .= '[-]';
        } elseif (ctype_digit($ch) || $ch === ' ') {
            $out .= $ch;
        }
    }
    return $out;
}

/**
 * Digit-bounded match so 3-1-1 does not also hit 3-1-10 / 13-1-1,
 * and 3.1.1 does not treat '.' as "any character".
 */
function poc_pathigam_search_condition($term) {
    $ors = [];
    foreach (poc_pathigam_code_variants($term) as $variant) {
        $escaped = poc_mysql_regexp_escape($variant);
        if ($escaped === '') {
            continue;
        }
        $pattern = '(^|[^0-9])' . $escaped . '([^0-9]|$)';
        $ors[] = "(SimilarWords REGEXP '$pattern' OR Pasuram REGEXP '$pattern' OR Prabandham REGEXP '$pattern' OR Word REGEXP '$pattern' OR Meaning REGEXP '$pattern')";
    }
    return '(' . implode(' OR ', $ors) . ')';
}

function poc_run_joined_search($conn, $conditions) {
    if (count($conditions) === 0) {
        return [null, null];
    }
    $sql_search = "SELECT DISTINCT PasuramsArthamTableTest.*
                   FROM PasuramsArthamTableTest
                   LEFT JOIN DivyaDesamTable 
                   ON PasuramsArthamTableTest.PasuramNumber = DivyaDesamTable.PasuramNumber 
                   WHERE " . implode(" AND ", $conditions) . " 
                   ORDER BY PasuramsArthamTableTest.PasuramNumber, PasuramsArthamTableTest.PattuNumber, PasuramsArthamTableTest.PadhamNumber, PasuramsArthamTableTest.Word";
    $result_search = $conn->query($sql_search);
    return [$sql_search, $result_search];
}

/**
 * Build WHERE conditions for padham / prabandham / alwar / divyadesam search.
 * prabandhamPrefix (counts page links) filters Prabandham column, not Pasuram text.
 */
function build_search_conditions($padhamPrefix, $prabandhamPrefix, $alwarPrefix, $divyadesamPrefix) {
    $conditions = [];
    $isPrabandham = ($prabandhamPrefix !== '');

    if ($isPrabandham) {
        $conditions[] = "Prabandham LIKE '$prabandhamPrefix%'";
    } elseif ($padhamPrefix !== '') {
        if (ctype_digit($padhamPrefix)) {
            $conditions[] = "PasuramsArthamTableTest.PasuramNumber = '$padhamPrefix'";
        } elseif (poc_is_pathigam_code($padhamPrefix)) {
            $conditions[] = poc_pathigam_search_condition($padhamPrefix);
        } else {
            $conditions[] = poc_text_search_condition($padhamPrefix);
        }
    }

    $alwarCond = poc_alwar_condition($alwarPrefix);
    if ($alwarCond !== null) {
        if ($isPrabandham) {
            // Thaniyans (PasuramNumber 0) are authored by Achariyars, so their Alzwar
            // is the Achariyar's name, not the Alwar's. Include them alongside the
            // Alwar's pasurams so the prabandham's thaniyan renders first.
            $conditions[] = "($alwarCond OR PasuramsArthamTableTest.PasuramNumber = 0)";
        } else {
            $conditions[] = $alwarCond;
        }
    }

    if ($divyadesamPrefix !== '') {
        $conditions[] = "DivyaDesamTable.DivyaDesam LIKE '%$divyadesamPrefix%'";
    }

    return $conditions;
}

// GET: prabandhamPrefix and/or padhamPrefix and/or alwarPrefix and/or divyadesamPrefix
if ($_SERVER["REQUEST_METHOD"] == "GET" && (
    isset($_GET['prabandhamPrefix']) || isset($_GET['padhamPrefix']) || isset($_GET['alwarPrefix']) || isset($_GET['divyadesamPrefix'])
)) {
    $prabandhamPrefix = isset($_GET['prabandhamPrefix']) ? mysqli_real_escape_string($conn, normalize_search_term($_GET['prabandhamPrefix'])) : '';
    $padhamPrefix = isset($_GET['padhamPrefix']) ? mysqli_real_escape_string($conn, normalize_search_term($_GET['padhamPrefix'])) : '';
    $alwarPrefix = isset($_GET['alwarPrefix']) ? mysqli_real_escape_string($conn, normalize_search_term($_GET['alwarPrefix'])) : '';
    $divyadesamPrefix = isset($_GET['divyadesamPrefix']) ? mysqli_real_escape_string($conn, normalize_search_term($_GET['divyadesamPrefix'])) : '';

    if ($padhamPrefix === "நித்யாநுஸந்தானம்") {
        $sql_search = "SELECT * 
                FROM PasuramsArthamTableTest 
                WHERE NithyaanusandhamIndex IS NOT NULL 
                ORDER BY NithyaanusandhamIndex, PasuramNumber";
        $result_search = $conn->query($sql_search);
    } else {
        $conditions = build_search_conditions($padhamPrefix, $prabandhamPrefix, $alwarPrefix, $divyadesamPrefix);
        list($sql_search, $result_search) = poc_run_joined_search($conn, $conditions);
    }
}

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $padhamPrefix = isset($_POST["padhamPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["padhamPrefix"])) : '';
    $alwarPrefix = isset($_POST["alwarPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["alwarPrefix"])) : '';
    $divyadesamPrefix = isset($_POST["divyadesamPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["divyadesamPrefix"])) : '';

    $conditions = build_search_conditions($padhamPrefix, '', $alwarPrefix, $divyadesamPrefix);

    if (count($conditions) > 0) {
        list($sql_search, $result_search) = poc_run_joined_search($conn, $conditions);
    } else {
        echo "Please enter search criteria.";
    }
}

if (!empty($sql_search) && $result_search && $result_search->num_rows > 0) {
    
    // Collect the prefixes entered by the user
    $searchTerms = [];
    
    // Check for each prefix and add it to the array if it's not empty
    if (!empty($prabandhamPrefix)) {
    $searchTerms[] = $prabandhamPrefix;
    } elseif (!empty($padhamPrefix)) {
    $searchTerms[] = $padhamPrefix; // Just the plain text, no HTML
    }
    if (!empty($alwarPrefix)) {
    $searchTerms[] = $alwarPrefix; // Just the plain text, no HTML
    }
    if (!empty($vazhithirunamaPrefix)) {
    $searchTerms[] = $vazhithirunamaPrefix; // Just the plain text, no HTML
    }
    if (!empty($divyadesamPrefix)) {
    $searchTerms[] = $divyadesamPrefix; // Just the plain text, no HTML
    }
    // Join the search terms with a separator
    $searchTermsString = implode(", ", $searchTerms);
    
    $grouped_results = array();

    while ($row_search = $result_search->fetch_assoc()) {
        $pasuramnumber = $row_search["PasuramNumber"];
        $prabandham = $row_search["Prabandham"];
        $pasuram = $row_search["Pasuram"];
        $pasuramWordsSplit = isset($row_search["PasuramWordsSplit"]) ? (string)$row_search["PasuramWordsSplit"] : '';
        $word = $row_search["Word"];
        $meaning = $row_search["Meaning"];
        $pattuNumber = $row_search["PattuNumber"];
        $Title = $row_search["Title"];
        $url = $row_search["url"];
        $alzwar = isset($row_search["Alzwar"]) ? $row_search["Alzwar"] : '';
        $SimilarWords = '';
        
        if (!empty($searchTerms)) {
            foreach ($searchTerms as $selectedPrefix) {
                // Use htmlspecialchars to prevent XSS attacks
                $highlightedPrefix = "<span class='highlight'>" . htmlspecialchars($selectedPrefix) . "</span>";
        
                // Instead of using htmlspecialchars() again here, directly replace the original values
                // Use str_ireplace for case-insensitive replacement
                $word = str_ireplace($selectedPrefix, $highlightedPrefix, $word);
                $pasuram = str_ireplace($selectedPrefix, $highlightedPrefix, $pasuram);
                $pasuramWordsSplit = str_ireplace($selectedPrefix, $highlightedPrefix, $pasuramWordsSplit);
                $SimilarWords = str_ireplace($selectedPrefix, $highlightedPrefix, $SimilarWords);
            }
        }
        
        // Color code Word in Red and Meaning in Blue
        $word = "<span style='color: red;'>$word</span>";
        $meaning = "<span style='color: blue;'>$meaning</span>";

        // Avoid a leading " - " when Word is empty (e.g. உபதேச ரத்னமாலை).
        if (trim(strip_tags($word)) === '') {
            $word_meaning_pair = $meaning;
        } else {
            $word_meaning_pair = "$word - $meaning";
        }

        // Check if this Pasuram has been seen before
        $key = "$prabandham-$pasuramnumber-$pasuram-$pattuNumber";
        if (!isset($grouped_results[$key])) {
            $grouped_results[$key] = array(
                'Prabandham' => $prabandham,
                'PasuramNumber' => $pasuramnumber,
                'Pasuram' => $pasuram,
                'PasuramWordsSplit' => $pasuramWordsSplit,
                'PattuNumber' => $pattuNumber,
                'Title' => $Title,
                'url' => $url,
                'Alzwar' => $alzwar,
                'WordMeaningPairs' => array(),
            );
        }

        // Add the Word-Meaning pair to the group
        $grouped_results[$key]['WordMeaningPairs'][] = $word_meaning_pair;
    }
    
    // After the while loop that populates $grouped_results
    $resultCount = count($grouped_results);

    // Display the search results header with the count
    echo "<div class='results-toolbar'>";
    echo "<h2 class='results-heading'>Search Results for: {$searchTermsString} ({$resultCount} results)</h2>";
    echo "<a href='#search-top' class='utility-link back-to-top' aria-label='Back to search'>Top</a>";
    echo "</div>";
    echo "<div class='results-wrap'>";
    echo "<table id='result-table'>
            <thead>
            <tr>
                <th style='width:5%'>Pasuram Number</th>
                <th style='width:22%'>Prabandham</th>
                <th style='width:22%'>Pasuram</th>
                <th style='width:22%'>Pasuram (split)</th>
                <th style='width:29%'>PadhaArtham</th>
            </tr>
            </thead>
            <tbody>";

    // Display the grouped results
    $rowNumber = 0; // Initialize row number

    foreach ($grouped_results as $grouped_result) {
        $rowNumber++;
    
        // Determine the background color based on even or odd row
        $backgroundColor = ($rowNumber % 2 == 0) ? '#f2f2f2' : '#ffffff';
    
        echo "<tr class='result-row' data-rowid='$rowNumber' style='background-color: $backgroundColor;'>";

        $isThaniyan = ((string)$grouped_result['PasuramNumber'] === '0');
        if ($isThaniyan) {
            $pattuDisplay = htmlspecialchars((string)$grouped_result['PattuNumber'], ENT_QUOTES, 'UTF-8');
            // Mobile: avoid "தனியன் தனியன் 2" — use short # label; keep தனியன் in the value.
            $numberLabel = '#';
            $numberDisplay = "<a href='test1.php?padhamPrefix=Thaniyan'>தனியன் {$pattuDisplay}</a>";
            $metaLabel = 'தனியன்';
            $pasuramLabel = 'Pasuram';
        } else {
            $numberLabel = 'Pasuram #';
            $numberDisplay = "<a href='test1.php?padhamPrefix={$grouped_result['PasuramNumber']}'>{$grouped_result['PasuramNumber']}</a>";
            $metaLabel = 'Prabandham';
            $pasuramLabel = 'Pasuram';
        }
        echo "<td class='col-number' data-label='{$numberLabel}'>{$numberDisplay}</td>";

        $prabandhamTrimmed = trim($grouped_result['Prabandham']);
        $prabandhamLink = "<a href='test1.php?prabandhamPrefix=" . urlencode($prabandhamTrimmed) . "'>" . htmlspecialchars($prabandhamTrimmed, ENT_QUOTES, 'UTF-8') . "</a>";
        // Keep Prabandham link text; for thaniyans the card/column label is தனியன்.
        // PattuNumber is shown in column 1 for thaniyans, so skip the trailing red copy.
        $metaExtra = $isThaniyan
            ? "<span style='color: green;'>{$grouped_result['Title']} </span>"
            : "<span style='color: green;'>{$grouped_result['Title']} </span> <span style ='color: red;'>{$grouped_result['PattuNumber']}</span>";
        echo "<td class='col-meta' data-label='{$metaLabel}'><span style='color: blue;'>{$prabandhamLink}</span><span style='color: rgb(51, 0, 255);'> || </span>{$metaExtra}</td>";

        // Keep verse line breaks via CSS (pre-line). Avoid nl2br + pre-wrap,
        // which doubles every newline into a blank gap on mobile.
        $pasuram = preg_replace("/\r\n|\r/", "\n", $grouped_result['Pasuram']);
        $pasuram = preg_replace("/\n{2,}/", "\n", $pasuram);
        echo "<td class='col-pasuram' data-label='{$pasuramLabel}'>";
        if ($isThaniyan) {
            $acharyar = trim((string)($grouped_result['Alzwar'] ?? ''));
            if ($acharyar !== '') {
                $acharyar = preg_replace("/\r\n|\r/", "\n", $acharyar);
                $acharyar = preg_replace("/\n{2,}/", "\n", $acharyar);
                echo "<div class='thaniyan-acharyar'>" . htmlspecialchars($acharyar, ENT_QUOTES, 'UTF-8') . "</div>";
            }
        }
        echo "<div class='pasuram-column'>$pasuram</div></td>";

        $pasuramSplit = isset($grouped_result['PasuramWordsSplit']) ? $grouped_result['PasuramWordsSplit'] : '';
        $pasuramSplit = preg_replace("/\r\n|\r/", "\n", $pasuramSplit);
        $pasuramSplit = preg_replace("/\n{2,}/", "\n", $pasuramSplit);
        echo "<td class='col-pasuram-split' data-label='Pasuram (split)'>";
        echo "<div class='pasuram-column'>$pasuramSplit</div></td>";

        $wordMeaningPairsColumn = implode("<br>", $grouped_result['WordMeaningPairs']);
        $wordMeaningPairsColumn = nl2br($wordMeaningPairsColumn);
        echo "<td class='col-padhaartham' data-label='PadhaArtham' style='background-color: $backgroundColor;'>";
        echo "<details class='padhaartham-details' open>";
        echo "<summary>பதவுரை Show / Hide</summary>";
        echo "<div class='padhaartham-body'>$wordMeaningPairsColumn</div>";
        echo "</details>";
        echo "</td>";
        echo "</tr>";
    }

    echo "</tbody></table>";
    echo "<div class='results-top-footer'><a href='#search-top' class='utility-link back-to-top' aria-label='Back to search'>Top</a></div>";
    echo "</div>";
}
?>


            </div>
    <script>
      document.addEventListener("DOMContentLoaded", function() {
            // Check if the user has performed a search
            var searchForm = document.getElementById("searchForm");
            var landingImages = document.getElementById("landingImages");
            var resultTable = document.getElementById("result-table"); 
            
            searchForm.addEventListener("submit", function() {
                // Hide the landing images when the user performs a search
                if (landingImages) {
                    landingImages.style.display = "none";
                }
                    // Make the result-table visible
                if (resultTable) {
                    resultTable.style.display = "block";
                }
            });
        });
        
        $(document).ready(function() {
            // Debounce function to limit the rate of AJAX requests
            function debounce(func, wait) {
                let timeout;
                return function() {
                    const context = this, args = arguments;
                    clearTimeout(timeout);
                    timeout = setTimeout(() => func.apply(context, args), wait);
                };
            }

            $("#Search").autocomplete({
                source: function(request, response) {
                    $.ajax({
                        url: "autocomplete.php",
                        type: "GET",
                        dataType: "json",
                        data: { query: request.term },
                        success: function(data) {
                            if (data.length > 0) {
                                response(data);
                            } else {
                                response([]);
                            }
                        }
                    });
                },
                minLength: 3,
                focus: function(event, ui) {
                    $("#Search").val(ui.item.label);
                    return false;
                },
                select: function(event, ui) {
                    $("#Search").val(ui.item.label);
                    return false;
                }
            }).data("ui-autocomplete")._renderMenu = function(ul, items) {
                var self = this;
                $.each(items, function(index, item) {
                    self._renderItemData(ul, item);
                });
            };

            // Apply debouncing to the search input
            $("#Search").on('input', debounce(function() {
                $(this).autocomplete("search");
            }, 300)); // 300ms debounce interval
        });
        

        document.addEventListener("DOMContentLoaded", function() {
            var url = new URL(window.location.href);
            var searchParams = url.searchParams;
        
            // Check if the URL has a 'search' parameter
            if (searchParams.has('search')) {
                // Remove the 'search' parameter
                searchParams.delete('search');
                
                // Update the URL without reloading the page
                var newUrl = url.origin + url.pathname + (searchParams.toString() ? '?' + searchParams.toString() : '');
                window.history.replaceState(null, '', newUrl);
            }

            // Mobile: collapse padhaartham by default; desktop: keep open
            function syncPadhaarthamOpen() {
                var isMobile = window.matchMedia('(max-width: 700px)').matches;
                document.querySelectorAll('.padhaartham-details').forEach(function(el) {
                    el.open = !isMobile;
                });
            }
            syncPadhaarthamOpen();
            window.matchMedia('(max-width: 700px)').addEventListener('change', syncPadhaarthamOpen);
        });

   </script>

</body>
</html>
