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
            background-color: #4CAF50;
            color: white;
            text-align: center;
            padding: 1em;
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
            background-color: #4CAF50;
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
            background-color: #4CAF50;
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


         
        }
    </style>
</head>
<body>
     <header>
        <img src="ThirumannKapu.jpeg" alt="Header Image">

        <center><h3 style="color: blue;">ஆழ்வார்கள் அருளிச்செய்த நாலாயிர திவ்யப் பிரபந்தம் - பதவுரை தேடல்</h3></center>
        <center> <h5 style="color: Yellow;"> திருப்பல்லாண்டு(1-12), திருப்பள்ளியெழுச்சி(917-926), திருப்பாவை(474-503), அமலனாதிபிரான் (927-935), கண்ணிநுண்சிறுத்தாம்பு (937-947) </h5></center>
        <center> <h5 style="color: Yellow;"> பெரியாழ்வார் திருமொழி(2-4 நீராட்டம்(152-161) 2-7 பூச்சூடல் (182-191) 2-8 காப்பிடல்(192-201) 5-4 சென்னியோங்கு(463-473)) </h5></center>
        <center> <h5 style="color: Yellow;">திருவாய்மொழி (1-1 உயர்வற 1-2 வீடுமின் 2-10 கிளரொளி 3-3 ஒழிவில்)</h5>  </center>
        
    </header>
            <div class="container">

                    <form action="" method="post">
                        <input type="text" id="Search" name="pasuramPrefix" placeholder="enter padham/word in tamil or english, pasuram number..ex மணிவண்ணா, Pallandu , 2-8-2, 940 etc">
                        <input type="submit" value="Search">
                        
                        
                        
                  
                        <label for="options">Select Prabandham:</label>  
                            <select name="options" id="options">
                                <option value="1">1</option>  
                                <option value="2">2</option>  
                                <option value="3">3</option>  
                                <option value="4">4</option> 
                            </select>   
                            <button type="submit">Submit</button>
                             
                              
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
                            // Check if option is selected
                            if (isset($_POST["options"])) {
                                $selectedOption = $_POST["options"];
                                
                                if ($selectedOption =="1"){
                                    $sql_search = "SELECT DISTINCT Prabandham FROM PasuramsArthamTableTest WHERE Prabandham IN ('திருப்பல்லாண்டு', 'திருப்பாவை', 'திருப்பள்ளியெழுச்சி', 'பெரியாழ்வார் திருமொழி', 'அமலனாதிபிரான்', 'கண்ணிநுண்சிறுத்தாம்பு')";
                                    $result_search = $conn->query($sql_search);
                                
                                echo "<p>You selected: Mudhalaayiram</p>";
                                
                                
                            } else {
                                echo "<p>No option selected.</p>";
                                }
                                
                            
                                if ($result_search->num_rows > 0) {
                                      // Output data of each row
                                    echo "<ul>";
                                    while($row = $result_search->fetch_assoc()) {
                                        echo "<li>" . $row["Prabandham"] . "</li>";
                                    }
                                    echo "</ul>";
                                } else {
                                   echo "No items found.";
                                }
                            }
                        }
                        
                        
                        if ($_SERVER["REQUEST_METHOD"] == "POST") {
                                $selectedPrefix = $_POST["pasuramPrefix"];
                        
                                if (is_numeric($selectedPrefix)) {
                                    $sql_search = "SELECT * FROM PasuramsArthamTable WHERE PasuramNumber = $selectedPrefix ORDER BY PasuramNumber, PattuNumber, PadhamNumber, Word";
                                } else {
                                    $sql_search = "SELECT * FROM PasuramsArthamTable WHERE SimilarWords LIKE '%$selectedPrefix%' ORDER BY PasuramNumber, PattuNumber, PadhamNumber, Word";
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
                                echo "<td>{$grouped_result['PasuramNumber']}</td>";
                            
                                
                                echo "<td><span style='color: blue;'>{$grouped_result['Prabandham']}</span><span style='color: rgb(51, 0, 255);'> || </span><span style='color: green;'>{$grouped_result['Title']} </span> <span style ='color: red;'>{$grouped_result['PattuNumber']}</span></p></td>";
                                echo "<td>{$grouped_result['Pasuram']}</td>";
                            
                                // Combine Word-Meaning pairs into a single column
                                $wordMeaningPairsColumn = implode("<br>", $grouped_result['WordMeaningPairs']);
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

    searchForm.addEventListener("submit", function() {
        // Hide the landing images when the user performs a search
        if (landingImages) {
            landingImages.style.display = "none";
        }
    });
  });
</script>
</body>
</html>
