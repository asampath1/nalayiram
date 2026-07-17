<?php
include('database.php');

// Fetch all SimilarWords from the main table
$sql = "SELECT DISTINCT SimilarWords FROM PasuramsArthamTable";
$result = $conn->query($sql);

echo $sql;

$data = array();
if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        // Extract individual words from the field
        $words = preg_split('/[,\s]+/', $row['SimilarWords']); // Split by comma or space
        
        // Convert all words to lowercase and trim spaces
        $temp_words = array_map('trim', array_map('strtolower', $words));
        
        // Remove duplicates
        $temp_words = array_unique($temp_words);
        
        // Merge words with data array
        $data = array_merge($data, $temp_words);
    }
    
    // Remove duplicates and sort the words alphabetically
    $data = array_unique($data);
    sort($data);
}

// Clear the SuggestedWords table
$conn->query("TRUNCATE TABLE SuggestedWords");

// Insert the processed words into the SuggestedWords table
$stmt = $conn->prepare("INSERT INTO SuggestedWords (Word) VALUES (?)");
foreach ($data as $word) {
    $stmt->bind_param("s", $word);
    $stmt->execute();
}

$stmt->close();
$conn->close();

echo "Suggested words updated successfully.";
?>
