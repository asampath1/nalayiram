<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
    <title>Pasura Artham Search</title>
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
        }
        .ui-menu-item {
            font-size: 14px;
            line-height: 1.6;
        }
        
    </style>
    <!-- jQuery library -->
        <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
        <!-- jQuery UI library for autocomplete -->
        <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
        <script>
            $(document).ready(function(){
                $("#Search").autocomplete({
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
                    minLength: 3, // Minimum characters before starting search
                    // Optional: format the autocomplete suggestions
                    focus: function( event, ui ) {
                        $( "#Search" ).val( ui.item.label );
                        return false;
                    },
                    select: function( event, ui ) {
                        $( "#Search" ).val( ui.item.label );
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
        <h4 style="color: white;">ஸ்ரீ காஞ்சி பிரதிவாதி பயங்கரம் அண்ணங்கராசாரியார் ஸ்வாமிகள் எழுதிய திவ்யார்த்த தீபிகை</h4>
        <h5 style="color: white;"><a href="release_notes.html" target="_blank">வெளியீட்டு குறிப்புகள் (Release Notes)</a></h5>
        <h5 style="color: white;">Search Tips: Enter padham/word in tamil or english, pasuram number, pasuram name.</h5>
        <h5 style="color: white;">ex மணிவண்ணா, Pallandu,பறை, vamanan,சென்னியோங்கு, 2-8-2, 940 etc. </h5>
        <h5 style="color: white;">See Release notes for more details</h5>
    </header>
            <div class="container">
                    <h5> <a href="#" id="customSubmit">சாற்றுமுறை</a></h5>
                    <form id="searchForm" action="" method="post">
                        <input type="text" id="Search" name="pasuramPrefix" placeholder="Enter padham/word in Tamil or English, pasuram number..ex மணிவண்ணா, Pallandu , 2-8-2, 940 etc">
                        <input type="submit" value="Search">
                    </form>
                <!-- Images to be displayed on the first visit -->
                    <div id="landingImages">
                        <img src="nambi.jpg" alt="Image 1" class="hidden">
                        <img src="manivannasearch.jpg" alt="Image 2" class="hidden">
                        <img src="punmai.jpg" alt="Image 2" class="hidden">
                        <img src="2-8search.jpg" alt="Image 2" class="hidden">
                        <!-- Add more images as needed -->
                    </div>
                    <?php
                        include('database.php'); 
                        
                        if ($_SERVER["REQUEST_METHOD"] == "POST") {
                                $selectedPrefix = $_POST["pasuramPrefix"];
                        
                                if (is_numeric($selectedPrefix)) {
                                    $sql_search = "SELECT * FROM PasuramsArthamTableURL WHERE PasuramNumber = $selectedPrefix ORDER BY PasuramNumber, PattuNumber, PadhamNumber, Word";
                                } else {
                                    $sql_search = "SELECT * FROM PasuramsArthamTableURL WHERE SimilarWords LIKE '%$selectedPrefix%' OR Pasuram LIKE '%$selectedPrefix%' ORDER BY PasuramNumber, PattuNumber, PadhamNumber, Word";
                                } 
                    
                                $result_search = $conn->query($sql_search);
                               // print($sql_search);
                               //print($result_search->num_rows);
                                
                                if ($result_search->num_rows > 0) {
                                    echo "<h2>Search Results for '{$selectedPrefix}':</h2>";
                                    echo "<table id='result-table'; style='width:100%'>
                                            <tr>
                                                <th style='width:5%'>Pasuram Number</th>
                                                <th style='width:10%'>Prabandham</th>
                                                <th style='width:35%'>Pasuram</th>
                                                <th style='width:50%'>PadhaArtham</th>
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
                                
                                    // Highlight the selected word
                                    $word = str_replace($selectedPrefix, "<span class='highlight'>$selectedPrefix</span>", $word);
                                    $pasuram = str_replace($selectedPrefix, "<span class='highlight'>$selectedPrefix</span>", $pasuram);
                                    $SimilarWords = str_replace($selectedPrefix, "<span class='highlight'>$selectedPrefix</span>", $SimilarWords);
                                    
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
                                            'url' =>$url,
                                            'WordMeaningPairs' => array(),
                                        );
                                    }
                                
                                    // Add the Word-Meaning pair to the group
                                    $grouped_results[$key]['WordMeaningPairs'][] = $word_meaning_pair;
                                }
                        
                        // Display the grouped results
                        
                            $rowNumber = 0; // Initialize row number
                                
                            foreach ($grouped_results as $grouped_result) {
                                $rowNumber++;
                            
                                // Determine the background color based on even or odd row
                                $backgroundColor = ($rowNumber % 2 == 0) ? '#f2f2f2' : '#ffffff';
                            
                                echo "<tr class='result-row' data-rowid='$rowNumber' style='background-color: $backgroundColor;'>";
                                echo "<td><a href='{$grouped_result['url']}' target='_blank'>{$grouped_result['PasuramNumber']}</a></td>";

                           
                                
                                echo "<td><span style='color: blue;'>{$grouped_result['Prabandham']}</span><span style='color: rgb(51, 0, 255);'> || </span><span style='color: green;'>{$grouped_result['Title']} </span> <span style ='color: red;'>{$grouped_result['PattuNumber']}</span></p></td>";
                                $pasuram = nl2br($grouped_result['Pasuram']);
                                echo "<td><div class='pasuram-column'>$pasuram</div></td>";
                                
                             

                            
                                    // Display debug information
                                   // echo "<pre>";
                                //    print_r($grouped_result['Pasuram']);
                                  //  echo "</pre>";
                                    
                                // Combine Word-Meaning pairs into a single column
                                $wordMeaningPairsColumn = implode("<br>", $grouped_result['WordMeaningPairs']);
                                // Replace newline characters with HTML line break tags
                                $wordMeaningPairsColumn = nl2br($wordMeaningPairsColumn);
                                echo "<td style='background-color: $backgroundColor;'>$wordMeaningPairsColumn</td>";

                            
                                echo "</tr>";
                            }
                                
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
        
        document.getElementById("customSubmit").addEventListener("click", function(event) {
            event.preventDefault();
            document.getElementById("Search").value = "சாற்றுமுறை";
            document.getElementById("searchForm").submit();
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
    </script>

</body>
</html>
