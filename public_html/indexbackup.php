<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <link rel="canonical" href="https://nalayiram.in/">
    <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
    <title>Backup — Nalayira Divya Prabandham Search</title>
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
            padding: 1em;
        }

        h5 {
            margin: 0;
            padding: 0;
        }
        
        header img {
            width: 200px; /* Adjust the width as needed */
            height: auto;
        }
        
        .container {
            width: 100%;
            box-sizing: border-box;
            padding: 20px; /* Adjust padding for container */
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
        /* CSS for mobile devices */
        @media only screen and (max-width: 600px) {
            .pasuram-column {
                white-space: pre-wrap; /* Maintain line breaks */
            }
        }
 
        .ui-autocomplete {
            max-height: 200px;
            overflow-y: auto;   /* prevent horizontal scrollbar */
            overflow-x: hidden; /* add padding to account for vertical scrollbar */
            z-index: 1000; /* ensure autocomplete is above other elements */
            background-color: lightblue;
            width: 300px; /* Set the width to match the text box */
            box-sizing: border-box; /* Ensure padding and border are included in the width */
        }
        }
        .ui-menu-item {
            font-size: 14px;
            line-height: 1.6;
        }
  
        .form-container {
            display: flex;
            justify-content: space-around; /* Distribute space evenly */
            align-items: center; /* Center the forms vertically */
        }
        .form-inline {
            display: flex; /* Align text input and button next to each other */
            align-items: center;
            margin-right: 10px; /* Optional: Adjust spacing between forms */
        }
        .form-inline input[type="text"] {
            margin-right: 5px; /* Optional: Adjust spacing between text input and button */
            width: 300px; /* Increase the text box length */
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
        <img src="ThirumannKapu.jpeg" alt="Header Image">
        <h3>ஆழ்வார்கள் அருளிச்செய்த நாலாயிர திவ்யப் பிரபந்தம் - பதவுரை தேடல்</h3>
        <h4 style="color: white;">ஸ்ரீ காஞ்சி பிரதிவாதி பயங்கரம் அண்ணங்கராசாரியார் ஸ்வாமிகள் எழுதிய திவ்யார்த்த தீபிகை , மற்றும் சில தொகுப்பில் ஸ்ரீ பெரியவாச்சான் பிள்ளை, ஸ்ரீ நம்பிள்ளை அவர்களின் அவதாரிகை உள்ளடங்கியது.</h4>
        <h5 style="color: white;">Search Tips: Enter Pasuram,padham/word in tamil or english, pasuram number.</h5>
        <h5 style="color: white;">eg. திருமாலை,மணிவண்ணா,thiruppavai,pallandu,பறை,vamanan,சென்னியோங்கு, 2-8-2, 940 etc. </h5>
        <h5 style="color: white;">See நாலாயிர திவ்யப்ரபந்தப் பாசுரங்களின் அடைவு for more details</h5>
    </header>
            <div class="container">
                    <h4>
                        <a href="https://nalayiram.in/index.php?padhamPrefix=Thaniyan" class="customSubmit">தனியன்கள்</a>
                        <a>   </a>
                        <a> |  </a>
                        <a>   </a>
                        <a href="https://nalayiram.in/index.php?padhamPrefix=நித்யாநுஸந்தானம்" class="customSubmit">நித்யாநுஸந்தானம்</a>
                        <a>   </a>
                        <a> |  </a>
                        <a>   </a>
                        <a href="https://nalayiram.in/index.php?padhamPrefix=சாற்றுமுறை" class="customSubmit">சாற்றுமுறை</a>
                        <a>   </a>
                        <a> |  </a>
                        <a>   </a>
                        <a href="divyaprabandham_counts.php?env=prod" class="customSubmit">திவ்யப்ரபந்தம்-எண்ணிக்கை</a>
                        <a>   </a>
                        <a> |  </a>
                        <a>   </a>
                        <a href="newreleasenotes.html" class="customSubmit">நாலாயிர திவ்யப்ரபந்தப் பாசுரங்களின் அடைவு</a>
                        <a>   </a>
                        <a> |  </a>
                        <a>   </a>
                        <a href="divyadesam_alwar_matrix.php?env=prod" class="customSubmit">திவ்யதேசம் -ஆழ்வார் -பாசுர எண்ணிக்கை அட்டவணை</a>

                    </h4>
  
<?php
// Prefill form fields from GET/POST (matrix / counts links use GET).
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
                            <input type="text" id="padhamSearch" name="padhamPrefix" value="<?php echo $formPadham; ?>" placeholder="Enter padham/word in Tamil or English, pasuram number..ex மணிவண்ணா, Pallandu , 2-8-2, 940 etc">
                             <label style="margin: 0 10px;"> and/or </label>
                            <input type="text" id="alzwarSearch" name="alwarPrefix" value="<?php echo $formAlwar; ?>" placeholder="Enter alzwar in Tamil or English">
                             <label style="margin: 0 10px;"> and/or </label>
                            <input type="text" id="divyadesamSearch" name="divyadesamPrefix" value="<?php echo $formDivyadesam; ?>" placeholder="Enter divyadesam in Tamil or English">
                            <input type="submit" value="Search">
                        </form>
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
 * Build Alzwar LIKE condition.
 * Autocomplete uses "English-Tamil"; matrix links pass plain Alzwar from DB.
 */
function prod_alwar_condition($alwarPrefix) {
    if ($alwarPrefix === '') {
        return null;
    }
    $parts = explode("-", $alwarPrefix, 2);
    if (isset($parts[1]) && trim($parts[1]) !== '') {
        $alwarPrefix = trim($parts[1]);
    } else {
        $alwarPrefix = trim($alwarPrefix);
    }
    if ($alwarPrefix === '') {
        return null;
    }
    return "Alzwar LIKE '%$alwarPrefix%'";
}

function prod_run_joined_search($conn, $conditions) {
    if (count($conditions) === 0) {
        return [null, null];
    }
    $sql_search = "SELECT DISTINCT PasuramsArthamTable.*
                   FROM PasuramsArthamTable
                   LEFT JOIN DivyaDesamTable 
                   ON PasuramsArthamTable.PasuramNumber = DivyaDesamTable.PasuramNumber 
                   WHERE " . implode(" AND ", $conditions) . " 
                   ORDER BY PasuramsArthamTable.PasuramNumber, PasuramsArthamTable.PattuNumber, PasuramsArthamTable.PadhamNumber, PasuramsArthamTable.Word";
    $result_search = $conn->query($sql_search);
    return [$sql_search, $result_search];
}

/**
 * Build WHERE conditions for padham / prabandham / alwar / divyadesam search.
 * prabandhamPrefix (counts page links) filters Prabandham column, not Pasuram text.
 */
function prod_build_search_conditions($padhamPrefix, $prabandhamPrefix, $alwarPrefix, $divyadesamPrefix) {
    $conditions = [];
    $isPrabandham = ($prabandhamPrefix !== '');

    if ($isPrabandham) {
        $conditions[] = "Prabandham LIKE '$prabandhamPrefix%'";
    } elseif ($padhamPrefix !== '') {
        if (is_numeric($padhamPrefix)) {
            $conditions[] = "PasuramsArthamTable.PasuramNumber = '$padhamPrefix'";
        } else {
            $conditions[] = "(SimilarWords LIKE '%$padhamPrefix%' OR Pasuram LIKE '%$padhamPrefix%')";
        }
    }

    $alwarCond = prod_alwar_condition($alwarPrefix);
    if ($alwarCond !== null) {
        if ($isPrabandham) {
            // Thaniyans (PasuramNumber 0) are authored by Achariyars, so their Alzwar
            // is the Achariyar's name, not the Alwar's. Include them alongside the
            // Alwar's pasurams so the prabandham's thaniyan renders first.
            $conditions[] = "($alwarCond OR PasuramsArthamTable.PasuramNumber = 0)";
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
                FROM PasuramsArthamTable 
                WHERE NithyaanusandhamIndex IS NOT NULL 
                ORDER BY NithyaanusandhamIndex, PasuramNumber";
        $result_search = $conn->query($sql_search);
    } else {
        $conditions = prod_build_search_conditions($padhamPrefix, $prabandhamPrefix, $alwarPrefix, $divyadesamPrefix);
        list($sql_search, $result_search) = prod_run_joined_search($conn, $conditions);
    }
}

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $padhamPrefix = isset($_POST["padhamPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["padhamPrefix"])) : '';
    $alwarPrefix = isset($_POST["alwarPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["alwarPrefix"])) : '';
    $divyadesamPrefix = isset($_POST["divyadesamPrefix"]) ? mysqli_real_escape_string($conn, normalize_search_term($_POST["divyadesamPrefix"])) : '';

    $conditions = prod_build_search_conditions($padhamPrefix, '', $alwarPrefix, $divyadesamPrefix);

    if (count($conditions) > 0) {
        list($sql_search, $result_search) = prod_run_joined_search($conn, $conditions);
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
    
    echo "<table id='result-table'; style='width:100%'>
            <tr>
                <th style='width:5%'>Pasuram Number</th>
                <th style='width:30%'>Prabandham</th>
                <th style='width:30%'>Pasuram</th>
                <th style='width:35%'>PadhaArtham</th>
            </tr>";

    $grouped_results = array();

    while ($row_search = $result_search->fetch_assoc()) {
        $pasuramnumber = $row_search["PasuramNumber"];
        $prabandham = $row_search["Prabandham"];
        $pasuram = $row_search["Pasuram"];
        $word = $row_search["Word"];
        $meaning = $row_search["Meaning"];
        $pattuNumber = $row_search["PattuNumber"];
        $Title = $row_search["Title"];
        $url = $row_search["url"];
        $SimilarWords = '';
        
        if (!empty($searchTerms)) {
            foreach ($searchTerms as $selectedPrefix) {
                // Use htmlspecialchars to prevent XSS attacks
                $highlightedPrefix = "<span class='highlight'>" . htmlspecialchars($selectedPrefix) . "</span>";
        
                // Instead of using htmlspecialchars() again here, directly replace the original values
                // Use str_ireplace for case-insensitive replacement
                $word = str_ireplace($selectedPrefix, $highlightedPrefix, $word);
                $pasuram = str_ireplace($selectedPrefix, $highlightedPrefix, $pasuram);
                $SimilarWords = str_ireplace($selectedPrefix, $highlightedPrefix, $SimilarWords);
            }
        }
        
        // Color code Word in Red and Meaning in Blue
        $word = "<span style='color: red;'>$word</span>";
        $meaning = "<span style='color: blue;'>$meaning</span>";
        
        // Combine Word and Meaning
        $word_meaning_pair = "$word - $meaning";


        // Check if this Pasuram has been seen before
        $key = "$prabandham-$pasuramnumber-$pasuram-$pattuNumber";
        if (!isset($grouped_results[$key])) {
            $grouped_results[$key] = array(
                'Prabandham' => $prabandham,
                'PasuramNumber' => $pasuramnumber,
                'Pasuram' => $pasuram,
                'PattuNumber' => $pattuNumber,
                'Title' => $Title,
                'url' => $url,
                'WordMeaningPairs' => array(),
            );
        }

        // Add the Word-Meaning pair to the group
        $grouped_results[$key]['WordMeaningPairs'][] = $word_meaning_pair;
    }
    
    // After the while loop that populates $grouped_results
    $resultCount = count($grouped_results);

    // Display the search results header with the count
    echo "<h2>Search Results for: {$searchTermsString} ({$resultCount} results)</h2>";

    // Display the grouped results
    $rowNumber = 0; // Initialize row number

    foreach ($grouped_results as $grouped_result) {
        $rowNumber++;
    
        // Determine the background color based on even or odd row
        $backgroundColor = ($rowNumber % 2 == 0) ? '#f2f2f2' : '#ffffff';
    
        echo "<tr class='result-row' data-rowid='$rowNumber' style='background-color: $backgroundColor;'>";
        
       // echo "<td>{$grouped_result['PasuramNumber']}</td>";
       // Add hyperlink for PasuramNumber
        $pasuramNumberLink = "<a href='index.php?padhamPrefix={$grouped_result['PasuramNumber']}'>{$grouped_result['PasuramNumber']}</a>";
        echo "<td>{$pasuramNumberLink}</td>";
        
        // Add hyperlink for Prabandham
        $prabandhamLink = "<a href='index.php?padhamPrefix=" . urlencode($grouped_result['Prabandham']) . "'>{$grouped_result['Prabandham']}</a>";
        echo "<td><span style='color: blue;'>{$prabandhamLink}</span><span style='color: rgb(51, 0, 255);'> || </span><span style='color: green;'>{$grouped_result['Title']} </span> <span style ='color: red;'>{$grouped_result['PattuNumber']}</span></td>";


    //    echo "<td><span style='color: blue;'>{$grouped_result['Prabandham']}</span><span style='color: rgb(51, 0, 255);'> || </span><span style='color: green;'>{$grouped_result['Title']} </span> <span style ='color: red;'>{$grouped_result['PattuNumber']}</span></p></td>";
      
        $pasuram = nl2br($grouped_result['Pasuram']);
        echo "<td><div class='pasuram-column'>$pasuram</div></td>";

        // Combine Word-Meaning pairs into a single column
        $wordMeaningPairsColumn = implode("<br>", $grouped_result['WordMeaningPairs']);
        // Replace newline characters with HTML line break tags
        $wordMeaningPairsColumn = nl2br($wordMeaningPairsColumn);
        echo "<td style='background-color: $backgroundColor;'>$wordMeaningPairsColumn</td>";
        echo "</tr>";
    }
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
        });

   </script>

</body>
</html>
